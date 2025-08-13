def p(a, t):
    left, h = 0, len(a) - 1
    for _ in range(len(a)):
        if left > h:
            break
        m = (left + h) // 2
        if a[m] == t:
            return m
        if a[m] < t:
            left = m + 1
        else:
            h = m - 1

    return -1
