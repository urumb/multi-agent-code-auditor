def common_ids(a: list, b: list) -> list:
    shared = []
    for x in a:
        if x in b:  # EXPECT: performance
            shared.append(x)
    return shared


def build_report(rows: list) -> str:
    out = ""
    for row in rows:
        out += ",".join(str(v) for v in row) + "\n"  # EXPECT: performance
    return out


def squares(values: list) -> list:
    result = []
    for v in values:
        result.append(v * v)  # EXPECT: performance
    return result


def has_duplicates(items: list) -> bool:
    for i in range(len(items)):
        for j in range(len(items)):  # EXPECT: performance
            if i != j and items[i] == items[j]:
                return True
    return False
