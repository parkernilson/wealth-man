def interval():
    for i in range(10):
        yield i

def action(interval):
    def _action(modifier):
        def _inner():
            for i in interval():
                yield modifier(i)
        return _inner
    return _action

def double(i):
    return i * 2

def apply(fn):
    def _apply(other_fn):
        return other_fn(fn)
    return _apply


def Pipe(*ops):
    cur = None
    for (i, op) in enumerate(ops):
        if i == 0:
            cur = op
        else: 
            cur = op(cur)
    return cur

pipe = Pipe(
    interval,
    action,
    apply(double)
)

gen = pipe()
output = [i for i in gen]

print(output)