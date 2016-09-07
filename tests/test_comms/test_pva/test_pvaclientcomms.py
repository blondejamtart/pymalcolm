import unittest
from mock import Mock, MagicMock, patch, call
from collections import OrderedDict

from malcolm.core.response import Error, Return, Delta
from malcolm.core.request import Post, Get
import pvaccess
pvaccess.Channel = MagicMock()
pvaccess.RpcClient = MagicMock()
pvaccess.PvObject = MagicMock()

from malcolm.comms.pva.pvaclientcomms import PvaClientComms


class TestPVAClientComms(unittest.TestCase):

    def setUp(self):
        self.ch = MagicMock()
        self.ch.get = MagicMock()
        pvaccess.Channel = MagicMock(return_value = self.ch)
        self.rpc = MagicMock()
        self.rpc.invoke = MagicMock()
        pvaccess.RpcClient = MagicMock(return_value = self.rpc)
        self.p = MagicMock()
        pvaccess.PvObject = MagicMock()

    def test_init(self):
        self.PVA = PvaClientComms(self.p)
        self.assertEqual("PvaClientComms", self.PVA.name)
        self.assertEqual(self.p, self.PVA.process)

    def test_send_get_to_server(self):
        self.PVA = PvaClientComms(self.p)
        self.PVA.send_to_caller = MagicMock()
        request = Get(endpoint=["ep1", "ep2"])
        self.PVA.send_to_server(request)
        pvaccess.Channel.assert_called_once()
        self.ch.get.assert_called_once()
        self.PVA.send_to_caller.assert_called_once()

    def test_send_post_to_server(self):
        self.PVA = PvaClientComms(self.p)
        self.PVA.send_to_caller = MagicMock()
        request = Post(endpoint=["ep1", "method1"], parameters={'arg1': 1})
        self.PVA.send_to_server(request)
        pvaccess.RpcClient.assert_called_once()
        self.rpc.invoke.assert_called_once()
        self.PVA.send_to_caller.assert_called_once()

