Server API
==========

.. _api:

Overview
~~~~~~~~

Look at project/namespace options. There is an option called ``publish``. When checked this option
allows browser clients to publish into channels of namespace directly. If client publishes a message
into channel directly - your application will not receive that message (it just goes through
Centrifuge towards subscribed clients). This pattern can be useful sometimes but in most
cases you need to receive event from client, process it - validate and save into database
and then broadcast to other connected clients. In this case you must not use channels which namespace
allows publishing.

The common pattern in this situation is receive new message via AJAX, do whatever you need
with it and then publish into Centrifuge using HTTP API. If your backend written on Python
you can use Cent API client. If you use other language don't worry - I will describe how to
communicate with Centrifuge API endpoint right now.

Centrifuge API url endpoint is ``/api/PROJECT_ID``, where PROJECT_ID must be replaced with your project ID
(you can find it in Centrifuge's web interface).

So if your Centrifuge domain is ``https://centrifuge.example.com`` and project ID is ``c54e65c4v6565``
then an API address will be ``https://centrifuge.example.com/api/c54e65c4v6565``.

All you need to do to use HTTP API is to send correctly constructed POST request to this endpoint.

API request must have two POST parameters: ``data`` and ``sign``.

``data`` is a json string representing command you want to send to Centrifuge (see below) and ``sign``
is an HMAC based on project secret key, project ID and ``data`` json string. This ``sign`` is used to
validate request.

``data`` is a json string made from object with two properties: ``method`` and ``params``.

``method`` is a name of action you want to do.
``params`` is an object with method arguments.

First lets see how to construct such request in Python. If Python is your language then you
don't have to implement this yourself as ``Cent`` module exists. But this example here can
be useful for someone who want to implement interaction with Centrifuge API in language for
which we don't have API client yet.

Lets imagine that you have a project with name ``development`` and secret key ``uutryx``. In web
interface of Centrifuge you can find HTTP API url, if you run Centrifuge locally then it
will be something like ``http://localhost:8000/api``

So you should send POST request to ``http://localhost:8000/api/development``.

.. code-block:: python

        from urllib2 import urlopen, Request
        from cent.core import generate_api_sign
        import json

        req = Request("http://localhost:8000/api/development")

        commands = [
            {
                "method": "publish",
                "params": {"channel": "docs", "data": {"json": True}}
            }
        ]
        encoded_data = json.dumps(commands)
        sign = generate_api_sign("uutryx", "development", encoded_data)

        data = urlencode({'sign': sign, 'data': encoded_data})
        response = urlopen(req, data, timeout=5)


See how to generate HMAC api sign in special chapter "Tokens and signatures"

There are lots of commands you can call. Some for managing project structure, some
for managing channels. Lets take a closer look on them.


Methods for managing channels
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Those are **publish**, **unsubscribe**, **presence**, **history**, **disconnect**

Lets just go through each of methods and look what they do and which params you need
to provide.

**publish** - send message into channel of namespace. ``data`` is an actual information
you want to send into channel. **It must be valid JSON**.

.. code-block:: javascript

    {
        "method": "publish",
        "params": {
            "channel": "CHANNEL NAME",
            "data": {}
        }
    }

**unsubscribe** - unsubscribe user with certain ID from channel.

.. code-block:: javascript

    {
        "method": "unsubscribe",
        "params": {
            "channel": "CHANNEL NAME",
            "user": "USER ID"
        }
    }

**disconnect** - disconnect user by user ID.

.. code-block:: javascript

    {
        "method": "disconnect",
        "params": {
            "user": "USER ID"
        }
    }

**presence** - get channel presence information (all clients currently subscribed on this channel).

.. code-block:: javascript

    {
        "method": "presence",
        "params": {
            "channel": "CHANNEL NAME"
        }
    }

**history** - get channel history information (list of last messages sent into channel).

.. code-block:: javascript

    {
        "method": "history",
        "params": {
            "channel": "CHANNEL NAME"
        }
    }


Cent
~~~~

Cent is a way to communicate with Centrifuge from python code or
from console (terminal).


To install:

.. code-block:: bash

    pip install cent


By default Cent uses `.centrc` configuration file from your home directory (``~/.centrc``).

Here is an example of config file's content:

.. code-block:: bash

    [football]
    address = http://localhost:8000/api
    key = PROJECT_KEY
    secret = 994021f2dc354d7893d88b90d430498e
    timeout = 5


The most obvious case of using Cent is broadcasting events into channels.

It is easy enough:

.. code-block:: bash

    cent football publish --params='{"channel": "news", "data": {"title": "World Cup 2018", "text": "some text..."}}'


- **cent** is the name of program
- **football** is the name of section in configuration file
- **publish** is the method name you want to call
- **--params** is a JSON string with method parameters, in case of publish you should provide channel and data parameters.


If request was successful you'll get something like this in response:

.. code-block:: bash

    {'error': None, 'body': True, 'method': 'publish'}


In case of any error you will get its description.


Cent contains Client class to send messages to Centrifuge from your python-powered backend:

.. code-block:: python

    from cent.core import Client

    client = Client("http://localhost:8000/api", "project_key", "project_secret")
    client.add(
        "publish", 
        {
            "channel": "python",
            "data": "hello world"
        }
    )
    result, error = client.send()

you can use ``add`` method to add several messages which will be sent. But up to 100 
(default, can be configured via Centrifuge configuration file using ``admin_api_message_limit`` option)


Python
~~~~~~

If your backend Python powered and you don't want to install Cent, you can just copy
``Client`` class from Cent source code (``cent.core.Client``) and use it as was shown
above.

Ruby
~~~~

`Oleg Bovykin <https://github.com/arrowcircle>`_ contributed an `implementation of Centrifuge API client for Ruby <https://github.com/centrifugal/centrifuge-ruby>`_.

Java
~~~~

There is an implementation of Centrifuge API client written by `Markus Coetzee <https://github.com/mcoetzee>`_.
The source code is available `here <https://github.com/mcoetzee/centrifuge-publisher>`_

PHP
~~~

There is an implementation of Centrifuge API client written by `Dmitriy Soldatenko <https://github.com/sl4mmer>`_.
The source code is available `here <https://github.com/sl4mmer/phpcent>`_

