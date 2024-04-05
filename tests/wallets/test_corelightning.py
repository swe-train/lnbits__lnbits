import pytest
from mock import Mock
from pytest_mock.plugin import MockerFixture

from lnbits.wallets.breez import settings
from lnbits.wallets.corelightning import CoreLightningWallet


class DataObject:
    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])


@pytest.mark.asyncio
async def test_status(mocker: MockerFixture):

    settings.corelightning_rpc = "1001"

    def fn_factory(data: str):
        def f1(*args, **kwargs):
            return data

        return f1

    d = {
        "help": fn_factory({"help": [{"command": "haaa"}]}),
        "listinvoices": fn_factory({"invoices": []}),
        "listfunds": fn_factory({"channels": []}),
    }

    m = _data_mock(d)

    # spy = mocker.spy(m, "help")
    mocker.patch("pyln.client.LightningRpc.__new__", m)

    wallet = CoreLightningWallet()
    spy = mocker.spy(wallet.ln, "help")

    # print("### spy 1", spy.call_count)

    # spy = mocker.spy(wallet.ln, "listfunds")
    status = await wallet.status()
    print("### status 1", status)

    print("### spy 2", spy.call_count)

    # m = Mock(side_effect=Exception("Boom!"))

    # mocker.patch.object(wallet.sdk_services, "node_info", m)
    # status = await wallet.status()
    # print("### status 2", status)


def _dict_to_object(data: dict) -> DataObject:
    d = {**data}
    for k in data:
        value = data[k]
        if isinstance(value, dict):
            d[k] = _dict_to_object(value)

    return DataObject(**d)


def _data_mock(data: dict) -> Mock:
    return Mock(return_value=_dict_to_object(data))
