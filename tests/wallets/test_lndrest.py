from json import JSONDecodeError

import pytest
from httpx import HTTPStatusError
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

from lnbits.wallets.corelightningrest import settings
from lnbits.wallets.lndrest import LndRestWallet

ENDPOINT = "http://127.0.0.1:8555"
MACAROON = "eNcRyPtEdMaCaRoOn"

headers = {
    "Grpc-Metadata-macaroon": MACAROON,
    "User-Agent": settings.user_agent,
}


bolt11_sample = str(
    "lnbc210n1pjlgal5sp5xr3uwlfm7ltum"
    + "djyukhys0z2rw6grgm8me9k4w9vn05zt"
    + "9svzzjspp5ud2jdfpaqn5c2k2vphatsj"
    + "ypfafyk8rcvkvwexnrhmwm94ex4jtqdq"
    + "u24hxjapq23jhxapqf9h8vmmfvdjscqp"
    + "jrzjqta942048v7qxh5x7pxwplhmtwfl"
    + "0f25cq23jh87rhx7lgrwwvv86r90guqq"
    + "nwgqqqqqqqqqqqqqqpsqyg9qxpqysgqy"
    + "lngsyg960lltngzy90e8n22v4j2hvjs4"
    + "l4ttuy79qqefjv8q87q9ft7uhwdjakvn"
    + "sgk44qyhalv6ust54x98whl3q635hkwgsyw8xgqjl7jwu",
)


# specify where the server should bind to
@pytest.fixture(scope="session")
def httpserver_listen_address():
    return ("127.0.0.1", 8555)


@pytest.mark.asyncio
async def test_status_no_balance(httpserver: HTTPServer):
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    httpserver.expect_request(
        uri="/v1/balance/channels", headers=headers, method="GET"
    ).respond_with_json({})

    wallet = LndRestWallet()

    status = await wallet.status()
    assert status.balance_msat == 0
    assert status.error_message == "{}"

    httpserver.check_assertions()


@pytest.mark.asyncio
async def test_status_with_balance(httpserver: HTTPServer):
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    server_response = {"balance": 21}
    httpserver.expect_request(
        uri="/v1/balance/channels", headers=headers, method="GET"
    ).respond_with_json(server_response)

    wallet = LndRestWallet()

    status = await wallet.status()
    assert status.balance_msat == 21_000
    assert status.error_message is None

    httpserver.check_assertions()


# @pytest.mark.asyncio
# async def test_status_with_error(httpserver: HTTPServer):
# todo: unify


@pytest.mark.asyncio
async def test_status_with_bad_json(httpserver: HTTPServer):
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    httpserver.expect_request(
        uri="/v1/balance/channels", headers=headers, method="GET"
    ).respond_with_data("test-text-error")

    wallet = LndRestWallet()

    status = await wallet.status()
    assert status.balance_msat == 0
    assert status.error_message == "test-text-error"

    httpserver.check_assertions()


@pytest.mark.asyncio
async def test_status_for_http_404(httpserver: HTTPServer):
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    httpserver.expect_request(
        uri="/v1/balance/channels", headers=headers, method="GET"
    ).respond_with_response(Response("Not Found", status=404))

    wallet = LndRestWallet()

    with pytest.raises(HTTPStatusError) as e_info:
        await wallet.status()

    assert e_info.match("Client error '404 NOT FOUND'")

    httpserver.check_assertions()


@pytest.mark.asyncio
async def test_status_for_server_down():
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    wallet = LndRestWallet()

    with pytest.raises(HTTPStatusError) as e_info:
        await wallet.status()

    assert e_info.match("Server error '500 INTERNAL SERVER ERROR'")


@pytest.mark.asyncio
async def test_status_for_missing_config():
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    # todo


@pytest.mark.asyncio
async def test_cleanup(httpserver: HTTPServer):
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    server_response = {"balance": 21}
    httpserver.expect_request(
        uri="/v1/balance/channels", headers=headers, method="GET"
    ).respond_with_json(server_response)

    wallet = LndRestWallet()

    status = await wallet.status()
    assert status.error_message is None
    assert status.balance_msat == 21_000

    # all calls should fail after this method is called
    await wallet.cleanup()

    with pytest.raises(RuntimeError) as e_info:
        # expected to fail
        await wallet.status()

    assert str(e_info.value) == "Cannot send a request, as the client has been closed."


@pytest.mark.asyncio
async def test_create_invoice_ok(httpserver: HTTPServer):
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    amount = 555
    server_resp = {
        "r_hash": "e35526a43d04e985594c0dfab848814f"
        + "524b1c786598ec9a63beddb2d726ac96",
        "payment_request": bolt11_sample,
    }

    # todo: data is different
    data = {"value": amount, "memo": "Test Invoice", "private": True}

    extra_data = {None: None, "expiry": 123}

    for key in extra_data:
        extra_server_resquest = {}
        if key:
            data[key] = extra_data[key]
            extra_server_resquest[key] = extra_data[key]

        httpserver.clear_all_handlers()
        httpserver.expect_request(
            uri="/v1/invoices",
            headers=headers,
            method="POST",
            json=data,  # todo: different
        ).respond_with_json(server_resp)

        wallet = LndRestWallet()

        invoice_resp = await wallet.create_invoice(
            amount=amount,
            memo="Test Invoice",
            label="test-label",
            description_hash=None,
            unhashed_description=None,
            **extra_server_resquest,
        )

        assert invoice_resp.success is True
        assert (
            invoice_resp.checking_id
            == "7b7e79dba6b8dddd387bdf39e7de1cd1"
            + "d7da6fce3cf35e1fe76e1bd5cefceb9f"
            + "7c79cf5aeb76de75d6f677bdba69cf7a"
        )  # todo: different
        assert invoice_resp.payment_request == server_resp["payment_request"]
        assert invoice_resp.error_message is None

        if key:
            del data[key]
        httpserver.check_assertions()


# todo
# @pytest.mark.asyncio
# async def test_create_invoice_unhashed_description(httpserver: HTTPServer):
#     settings.lnd_rest_endpoint = ENDPOINT
#     settings.lnd_rest_macaroon = MACAROON
#     settings.lnd_rest_cert = ""


@pytest.mark.asyncio
async def test_create_invoice_error(httpserver: HTTPServer):
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    amount = 555
    server_resp = {"error": "Test Error"}

    data = {"value": amount, "memo": "Test Invoice", "private": True}

    httpserver.expect_request(
        uri="/v1/invoices",
        headers=headers,
        method="POST",
        json=data,
    ).respond_with_json(
        server_resp, 400
    )  # todo: extra HTTP status

    wallet = LndRestWallet()

    invoice_resp = await wallet.create_invoice(
        amount=amount,
        memo="Test Invoice",
        label="test-label",
    )

    assert invoice_resp.success is False
    assert invoice_resp.checking_id is None
    assert invoice_resp.payment_request is None
    assert invoice_resp.error_message == "Test Error"

    httpserver.check_assertions()


@pytest.mark.asyncio
async def test_create_invoice_for_http_404(httpserver: HTTPServer):
    settings.lnd_rest_endpoint = ENDPOINT
    settings.lnd_rest_macaroon = MACAROON
    settings.lnd_rest_cert = ""

    amount = 555

    data = {
        "amount": amount * 1000,
        "description": "Test Invoice",
        "label": "test-label",
    }

    data = {"value": amount, "memo": "Test Invoice", "private": True}

    httpserver.expect_request(
        uri="/v1/invoices", headers=headers, method="POST", json=data
    ).respond_with_response(Response("Not Found", status=404))

    wallet = LndRestWallet()

    with pytest.raises(JSONDecodeError) as e_info:
        await wallet.create_invoice(
            amount=amount,
            memo="Test Invoice",
            label="test-label",
        )

    # todo: fix class, it should not throw on 404
    assert str(e_info.value) == "Expecting value: line 1 column 1 (char 0)"

    httpserver.check_assertions()