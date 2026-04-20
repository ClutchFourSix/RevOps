from rapidfuzz import fuzz


def dedupe_companies(companies):
    unique = []

    for c in companies:
        duplicate = False
        for u in unique:
            if fuzz.ratio(c["name"], u["name"]) > 90:
                duplicate = True
                break

        if not duplicate:
            unique.append(c)

    return unique
