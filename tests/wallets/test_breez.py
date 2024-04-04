import breez_sdk
import pytest
from mock import Mock
from pytest_mock.plugin import MockerFixture

from lnbits.wallets.breez import BreezSdkWallet, settings


class DataObject:
    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])


@pytest.mark.asyncio
async def test_status(mocker: MockerFixture):

    settings.breez_api_key = "100"
    settings.breez_greenlight_seed = (
        "push divert icon era bracket fade much kind reason injury suffer muffin"
    )
    settings.breez_greenlight_device_key = "tests/wallets/data/certificates/cert.pem"
    settings.breez_greenlight_device_cert = "tests/wallets/data/certificates/breez.crt"

    mocker.patch("breez_sdk.connect").return_value({})
    wallet = BreezSdkWallet()

    mocker.patch.object(
        wallet.sdk_services,
        "node_info",
        _data_mock({"channels_balance_msat": 25000000}),
    )

    status = await wallet.status()
    print("### status 1", status)

    assert status.balance_msat == 25000000
    assert status.error_message is None

    m = Mock(side_effect=Exception("Boom!"))

    mocker.patch.object(wallet.sdk_services, "node_info", m)
    status = await wallet.status()
    print("### status 2", status)


@pytest.mark.asyncio
async def test_create_invoice(mocker: MockerFixture):

    settings.breez_api_key = "100"
    settings.breez_greenlight_seed = (
        "push divert icon era bracket fade much kind reason injury suffer muffin"
    )
    settings.breez_greenlight_device_key = "tests/wallets/data/certificates/cert.pem"
    settings.breez_greenlight_device_cert = "tests/wallets/data/certificates/breez.crt"

    def fn_factory(data: str):
        def f1(*args, **kwargs):
            print("### f1", args)
            return data

        return f1

    d = {
        "receive_payment": fn_factory(
            {"ln_invoice": {"payment_hash": "000001", "bolt11": "ln1234"}}
        )
    }
    m = _data_mock(d)
    mocker.patch("breez_sdk.connect").return_value(m)
    wallet = BreezSdkWallet()

    # mocker.patch.object(
    #     wallet.sdk_services,
    #     "receive_payment",
    #     _data_mock({"ln_invoice": {"payment_hash": "000001", "bolt11": "ln1234"}}),
    # )

    spy = mocker.spy(wallet.sdk_services, "receive_payment")
    invoice_response = await wallet.create_invoice(50, "Test Invoice")
    print("### invoice_response 1", invoice_response)

    assert spy.call_count == 1

    resp = breez_sdk.ReceivePaymentRequest(
        amount_msat=50 * 1000,  # breez uses msat
        description="Test Invoice",
        preimage=None,
        opening_fee_params=None,
        use_description_hash=None,
    )
    spy.assert_called_with(resp)

    print("### spy.call_args 1", spy.call_args)
    print("### spy.call_args 2", getattr(spy.call_args, "amount_msat"))

    # m = Mock(side_effect=Exception("Boom!"))

    # mocker.patch.object(wallet.sdk_services, "receive_payment", m)
    # invoice_response = await wallet.create_invoice(50, "Test Invoice")
    # print("### invoice_response 2", invoice_response)


def _dict_to_object(data: dict) -> DataObject:
    d = {**data}
    for k in data:
        value = data[k]
        if isinstance(value, dict):
            d[k] = _dict_to_object(value)

    return DataObject(**d)


def _data_mock(data: dict) -> Mock:
    return Mock(return_value=_dict_to_object(data))
