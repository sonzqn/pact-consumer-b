"""pact test for user service client"""

import atexit
import logging
import os

import pytest
from pact import Consumer, Like, Provider

from src.consumer import UserConsumer

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

import socket
from contextlib import closing


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


# Define where to run the mock server, for the consumer to connect to. These
# are the defaults so may be omitted
PACT_MOCK_HOST = "localhost"
PACT_MOCK_PORT = find_free_port()

# Where to output the JSON Pact files created by any tests
PACT_DIR = os.path.dirname(os.path.realpath(__file__)) + "/pacts"


@pytest.fixture
def consumer() -> UserConsumer:
    return UserConsumer("http://{host}:{port}".format(host=PACT_MOCK_HOST, port=PACT_MOCK_PORT))


@pytest.fixture(scope="session")
def pact(request):
    """Setup a Pact Consumer, which provides the Provider mock service. This
    will generate and optionally publish Pacts to the Pact Broker"""

    pact = Consumer("consumer-b").has_pact_with(
        Provider("provider-x"),
        host_name=PACT_MOCK_HOST,
        port=PACT_MOCK_PORT,
        pact_dir=PACT_DIR,
    )

    pact.start_service()

    # Make sure the Pact mocked provider is stopped when we finish, otherwise
    # port 1234 may become blocked
    atexit.register(pact.stop_service)

    yield pact

    # This will stop the Pact mock server, and if publish is True, submit Pacts
    # to the Pact Broker
    pact.stop_service()


def test_get_user_non_admin(pact, consumer):
    # Define the Matcher; the expected structure and content of the response
    expected = {
        "code": Like("CC_001"),
        "name": Like("28 Degrees"),
        "id": Like(10),
    }

    # Define the expected behaviour of the Provider. This determines how the
    # Pact mock provider will behave. In this case, we expect a body which is
    # "Like" the structure defined above. This means the mock provider will
    # return the EXACT content where defined, e.g. UserA for name, and SOME
    # appropriate content e.g. for ip_address.
    (
        pact.given("product with ID 10 exists")
            .upon_receiving("Get product with ID 10")
            .with_request(
            "get",
            "/product/10",
            body=None,
            headers={
                "Authorization": "Bearer AAABd9yHUjI="
            }
        ).will_respond_with(
            200,
            headers={
                "Content-Type": "application/json"
            },
            body=Like(expected)
        )
    )

    with pact:
        # Perform the actual request
        user = consumer.get_product(10)

        # In this case the mock Provider will have returned a valid response
        assert user.id == 10

        # Make sure that all interactions defined occurred
        pact.verify()
