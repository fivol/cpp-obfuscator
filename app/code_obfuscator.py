from lang_objects import *


class CppCodeObfuscator:
    c_elements = [
        CSpaces,
        CInclude,
        CClass,
        CFunction,
        CVariableInit,
        CWord,
        CSymbol
    ]

    def __init__(self, source_code):
        self.source_code = source_code
        self.code_elements = []
        self.processed_code = ""

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'r') as f:
            return CppCodeObfuscator(f.read())

    def print(self):
        pprint(list(filter(lambda x: not isinstance(x, CSpaces), self.code_elements)))

    def obfuscate(self):
        code = self.source_code
        code_elements = self._parse(code)

        self.processed_code = ''.join(map(lambda x: x.refactor(), code_elements))

    def write_file(self, filename):
        with open(filename, 'w') as f:
            f.write(self.processed_code)

    @classmethod
    def _parse(cls, code):
        iterator = StrIterator(code, 0)
        code_elements = []
        while not iterator.is_end():
            for CPart in cls.c_elements:
                c_part = CPart.parse(iterator)
                if c_part:
                    code_elements.append(c_part)
                    break
        return code_elements
