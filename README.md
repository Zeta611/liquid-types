# Liquid Types

This is a rudimentary implementation of liquid types written in Python for the course CS294: Modern Programming Tools.

Check a source file:

```sh
uv run liquid-types check example.lq
```

For example, save this as `example.lq`:

```ocaml
(
    val inc : x:int => int[v | v = x + 1];
    let inc = (x) => {
        let one = 1;
        x + one
    };

    let n = 41;
    inc(n)
) : int[v | v = 42]
```

The command prints `example.lq: type checks` on success and exits with status 0.

Evaluate the file with

```sh
uv run liquid-types run example.lq
```

For this example, `run` prints `42`.


## Testing
Run the tests from the project root:

```sh
uv run python -m unittest discover -s tests -t . -v
```
