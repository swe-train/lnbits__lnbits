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
    print("### status", status)


def _data_mock(data: dict) -> Mock:
    return Mock(return_value=DataObject(**data))
