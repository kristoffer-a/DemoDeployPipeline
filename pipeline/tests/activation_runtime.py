"""Small offline runner for generated activation actions, not a Power Automate emulator.

Executes the emitted expressions/actions against a fake Dataverse inventory. This
checks policy decisions and write ordering; connector/runtime acceptance still needs TEST.
"""
import copy
import json
import re

import jsonschema


class RunFailed(RuntimeError):
    pass


class Runtime:
    def __init__(self, policy, inventory, *, fail_write=None, stale_readback=False, next_link=None):
        self.trigger = {"manifest": json.dumps(policy) if not isinstance(policy, str) else policy}
        self.inventory = copy.deepcopy(inventory)
        self.original = copy.deepcopy(inventory)
        self.results = {"Config": {"RunImport": True}}
        self.variables = {"FailMessage": ""}
        self.loops = {}
        self.row = None
        self.writes = []
        self.fail_write = fail_write
        self.stale_readback = stale_readback
        self.next_link = next_link

    def expr(self, text):
        if not isinstance(text, str) or not text.startswith('@'):
            return text
        source = text[1:]
        tokens = re.findall(r"'(?:[^']|'')*'|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|\?\[|[(),\]]", source)
        assert ''.join(tokens) == re.sub(r'\s+(?=(?:[^\']*\'[^\']*\')*[^\']*$)', '', source), source
        pos = 0

        def parse():
            nonlocal pos
            token = tokens[pos]
            pos += 1
            if token.startswith("'"):
                value = token[1:-1].replace("''", "'")
            elif token.isdigit():
                value = int(token)
            elif token in ('true', 'false'):
                value = token == 'true'
            else:
                assert tokens[pos] == '(', (source, tokens[pos])
                pos += 1
                args = []
                while tokens[pos] != ')':
                    args.append(parse())
                    if tokens[pos] == ',':
                        pos += 1
                    else:
                        assert tokens[pos] == ')'
                pos += 1
                value = self.call(token, args)
            while pos < len(tokens) and tokens[pos] == '?[':
                pos += 1
                key = parse()
                assert tokens[pos] == ']'
                pos += 1
                value = value.get(key) if isinstance(value, dict) else None
            return value

        result = parse()
        assert pos == len(tokens), source
        return result

    def call(self, name, args):
        functions = {
            'triggerBody': lambda: self.trigger,
            'body': lambda n: self.results[n], 'outputs': lambda n: self.results[n],
            'item': lambda: self.row, 'items': lambda n: self.loops[n],
            'variables': lambda n: self.variables[n],
            'toLower': lambda x: x.lower(), 'empty': lambda x: not x,
            'not': lambda x: not x, 'equals': lambda a, b: type(a) is type(b) and a == b,
            'contains': lambda a, b: b in a, 'length': len,
            'union': lambda a, b: list(dict.fromkeys(a + b)),
            'intersection': lambda a, b: list(dict.fromkeys(x for x in a if x in b)),
            'first': lambda x: x[0], 'string': str, 'int': int,
            'concat': lambda *x: ''.join(x), 'if': lambda c, a, b: a if c else b,
            'add': lambda a, b: a + b, 'and': lambda *args: all(args),
        }
        return functions[name](*args)

    def condition(self, expression):
        name, args = next(iter(expression.items()))
        if name == 'not':
            return not self.condition(args)
        if name == 'or':
            return any(self.condition(a) for a in args)
        if name == 'and':
            return all(self.condition(a) for a in args)
        a, b = (self.expr(x) for x in args)
        return {'equals': lambda: type(a) is type(b) and a == b, 'greater': lambda: a > b}[name]()

    def run(self, actions):
        for name, action in actions.items():
            # seq's dependencies are verified separately. An action failure aborts this scope.
            kind = action['type']
            inp = action.get('inputs', {})
            if kind == 'ParseJson':
                value = json.loads(self.expr(inp['content']))
                jsonschema.Draft4Validator(inp['schema']).validate(value)
            elif kind in ('Select', 'Query'):
                value = []
                for row in self.expr(inp['from']):
                    self.row = row
                    if kind == 'Select':
                        value.append(self.expr(inp['select']))
                    elif self.expr(inp['where']):
                        value.append(row)
            elif kind == 'If':
                branch = action.get('actions', {}) if self.condition(action['expression']) else action.get('else', {}).get('actions', {})
                self.run(branch)
                value = None
            elif kind == 'Foreach':
                failure = None
                for row in self.expr(action['foreach']):
                    self.loops[name] = row
                    try:
                        self.run(action['actions'])
                    except RunFailed as error:
                        # Sequential iterations continue after failure in Power Automate.
                        failure = failure or error
                if failure:
                    raise failure
                value = None
            elif kind == 'SetVariable':
                self.variables[inp['name']] = self.expr(inp['value'])
                value = None
            elif kind == 'Compose':
                try:
                    value = self.expr(inp)
                except ValueError as e:
                    raise RunFailed(self.variables.get('FailMessage')) from e
            elif kind == 'OpenApiConnection':
                operation = inp['host']['operationId']
                if operation == 'ListRecordsWithOrganization':
                    rows = self.original if self.stale_readback and name == 'Verify_flows' else self.inventory
                    value = {'value': copy.deepcopy(rows)}
                    if self.next_link:
                        value['@odata.nextLink'] = self.next_link
                elif operation == 'UpdateOnlyRecordWithOrganization':
                    params = inp['parameters']
                    wid = self.expr(params['recordId'])
                    if wid == self.fail_write:
                        raise RunFailed('Injected write failure')
                    self.writes.append((wid, params['item']['statecode']))
                    next(r for r in self.inventory if r['workflowid'].lower() == wid).update(params['item'])
                    value = {}
                else:
                    raise AssertionError(operation)
            else:
                raise AssertionError(kind)
            self.results[name] = value
