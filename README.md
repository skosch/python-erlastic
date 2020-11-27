# Erlastic #

## Installation

```bash
pip3 install git+https://github.com/skosch/python-erlastic
```

## Usage ##

Erlastic allows you to serialize/deserialize python objects into 
[erlang binary term](http://erlang.org/doc/apps/erts/erl_ext_dist.html).

Basic usage is :
```python
import erlastic
py_struct = erlastic.decode(binary_term)
binary = erlastic.encode(py_struct)
```
## Sending and receiving from Python

The library contains also a function to use python with erlastic in an erlang
port to communicate erlang binary term : `port_communication()` which return
`(mailbox,port)`. They are both python coroutines (executed generator) so you
can communicate with erlang coroutine using python abstractions :

- `mailbox` waits for port message in stdin, iterating over messages decoded
   from binary erlang term format.
- `port` waits for `send(python_struct)` (http://docs.python.org/3.3/reference/expressions.html#generator.send)
  then encode `python_struct` into binary term format and send it to the erlang port via stdout.

So for instance, if you want to create a Python script which
receives a 2-tuple of numbers `{A, B}` and returns `{ok, A/B}` or `{error, divisionbyzero}`, 
then you can use:
```python
from erlastic import port_connection, Atom as A
mailbox, port = port_connection()

for (a, b) in mailbox:
  if b != 0:
    port.send((A("ok"),a/b))
  else:
    port.send((A("error"), A("divisionbyzero")))
```

### Converting between bytes and strings
Strings are sent as raw bytes with unknown character encoding. To recursively convert data from raw bytes to Python strings, you can pass received data through a function like
```python
def convert_to_string(data):
    if isinstance(data, bytes):  return data.decode('ascii') # or 'utf-8' ...
    if isinstance(data, dict):   return dict(map(convert_to_string, data.items()))
    if isinstance(data, tuple):  return tuple(map(convert_to_string, data))
    if isinstance(data, list):   return list(map(convert_to_string, data))
    return data
```

### Printing to the terminal from iex
If the output of Python's `print` statements aren't showing up in your terminal, try printing to stderr instead, using a function like `eprint` below:
```python
import sys
import pprint

pprinter = pprint.PrettyPrinter(indent=2, stream=sys.stderr, width=80)
def eprint(*args):
    pprinter.pprint(args)
```

## Sending and receiving from Erlang or Elixir
and at the erlang side, use `-u` python parameter to prevent python output
buffering, use 4 bytes packet length because it is the configuration used by
the python generators.
```erlang
Port = open_port({spawn,"python3 -u division.py"},[binary,{packet,4}]),
Div = fun(A,B)->
  Port ! {self(),{command,term_to_binary({A,B})}},
  receive {Port,{data,Bin}}->binary_to_term(Bin) after 1000->{error,timeout} end
end,
io:format("send {A,B}=~p, python result : ~p~n",[{32,10},Div(32,10)]),
io:format("send {A,B}=~p, python result : ~p~n",[{2,0},Div(2,0)]),
io:format("send {A,B}=~p, python result : ~p~n",[{1,1},Div(1,1)])
```
or in Elixir:
```elixir
port = Port.open({:spawn,'python3 division.py'},[:binary|[packet: 4]])
div = fn(a, b)->
  port <- {self, {:command,term_to_binary({a, b})}}
  receive do
    {^port, {:data, b}} -> binary_to_term(b)
  after
    100-> {:error, :timeout}
  end
end

IO.puts "send {a, b}={32, 10}, python result: #{inspect div.(32, 10)}"
IO.puts "send {a, b}={2, 0}, python result: #{inspect div.(2, 0)}"
IO.puts "send {a, b}={1, 1}, python result: #{inspect div.(1, 1)}"
```
