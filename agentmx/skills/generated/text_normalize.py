# generated at 1756925613 run_id=9e65104a023e494e9779b59cbbb5d35f spec_hash=cfb476f0bcf8
class TextNormalizeSkill:
    def run(self, path: str) -> str:
        import os
        p = os.path.abspath(path)
        with open(p, 'r', encoding='utf-8') as f:
            txt = f.read()
        norm = '\n'.join(line.strip() for line in txt.splitlines()) + '\n'
        out = p + '.norm.txt'
        with open(out, 'w', encoding='utf-8') as f:
            f.write(norm)
        return out
