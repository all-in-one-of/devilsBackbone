def match(string, sep=('[', ']')):
    stack = list()
    for i, c in enumerate(string):
        if c == sep[0]:
            stack.append(i)
        elif c == sep[1] and stack:
            start = stack.pop()
            yield (len(stack), string[start + 1:i])
