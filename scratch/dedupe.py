import sys

def run():
    with open(".gitignore", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    seen = set()
    out = []
    
    for line in lines:
        stripped = line.strip()
        # Keep empty lines and comments (if we want, but wait, if it's an exact duplicate block, we want to remove the whole block)
        # Actually, if we just keep the first occurrence of non-empty lines, it will strip duplicates.
        if stripped == '':
            if len(out) > 0 and out[-1].strip() != '':
                out.append(line)
            continue
        
        # Don't deduplicate comments, except maybe they are also part of the duplicated block.
        # It's better to just track all lines if we are removing a duplicate block.
        if stripped not in seen:
            seen.add(stripped)
            out.append(line)
        elif stripped.startswith('#'):
            # It's a duplicate comment, might be part of the duplicated block
            pass

    # Ensure own_docs/ is there
    if "own_docs/" not in seen:
        out.append("own_docs/\n")

    with open(".gitignore", "w", encoding="utf-8") as f:
        f.writelines(out)

if __name__ == '__main__':
    run()
