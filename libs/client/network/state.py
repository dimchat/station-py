# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

import time
from abc import ABC
from typing import Optional

from startrek.fsm import Context, BaseTransition, BaseState, AutoMachine
from startrek import GateStatus

from .server import Server


class StateMachine(AutoMachine, Context):

    def __init__(self, server: Server):
        super().__init__(default=ServerState.DEFAULT)
        self.delegate = server
        self.__session: Optional[str] = None  # session key
        # init states
        builder = self._create_state_builder()
        self.__set_state(state=builder.get_default_state())
        self.__set_state(state=builder.get_connecting_state())
        self.__set_state(state=builder.get_connected_state())
        self.__set_state(state=builder.get_handshaking_state())
        self.__set_state(state=builder.get_running_state())
        self.__set_state(state=builder.get_error_state())

    # noinspection PyMethodMayBeStatic
    def _create_state_builder(self):
        return StateBuilder(transition_builder=TransitionBuilder())

    def __set_state(self, state):
        self.add_state(name=state.name, state=state)

    @property  # Override
    def current_state(self):  # -> ServerState:
        state = super().current_state
        if state is None:
            state = self.default_state
        return state

    @current_state.setter
    def current_state(self, state):
        AutoMachine.current_state.__set__(self, state)

    @property  # Override
    def context(self) -> Context:
        return self

    @property
    def server(self) -> Server:
        delegate = self.delegate
        assert isinstance(delegate, Server), 'server error: %s' % delegate
        return delegate

    @property
    def current_user(self):
        server = self.server
        if server is not None:
            return server.current_user

    @property
    def status(self) -> GateStatus:
        server = self.server
        if server is None:
            return GateStatus.ERROR
        return server.status

    @property
    def session_key(self) -> Optional[str]:
        return self.__session

    @session_key.setter
    def session_key(self, session: str):
        self.__session = session


class StateTransition(BaseTransition[StateMachine], ABC):
    pass


class ServerState(BaseState[StateMachine, StateTransition]):
    """
        Server State
        ~~~~~~~~~~~~

        Defined for indicating session states

            DEFAULT     - initialized
            CONNECTING  - connecting to the server
            CONNECTED   - connected to the server
            HANDSHAKING - trying to log in
            RUNNING     - handshake accepted
            ERROR       - network error
    """

    DEFAULT = 'default'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    HANDSHAKING = 'handshaking'
    RUNNING = 'running'
    ERROR = 'error'

    def __init__(self, name: str):
        super().__init__()
        self.__name = name
        self.__time: int = 0  # enter time

    @property
    def name(self) -> str:
        return self.__name

    @property
    def enter_time(self) -> int:
        return self.__time

    def __str__(self) -> str:
        return self.__name

    def __repr__(self) -> str:
        return self.__name

    def __eq__(self, other) -> bool:
        if self is other:
            return True
        elif isinstance(other, ServerState):
            return self.__name == other.name
        elif isinstance(other, str):
            return self.__name == other
        else:
            return False

    def __ne__(self, other) -> bool:
        if self is other:
            return False
        elif isinstance(other, ServerState):
            return self.__name != other.name
        elif isinstance(other, str):
            return self.__name != other
        else:
            return True

    def on_enter(self, ctx: StateMachine):
        self.__time = int(time.time())

    def on_exit(self, ctx: StateMachine):
        self.__time = 0

    def on_pause(self, ctx: StateMachine):
        pass

    def on_resume(self, ctx: StateMachine):
        pass


#
#   Builders
#

class StateBuilder:

    def __init__(self, transition_builder):
        super().__init__()
        self.__builder = transition_builder

    # noinspection PyMethodMayBeStatic
    def get_named_state(self, name: str) -> ServerState:
        return ServerState(name=name)

    def get_default_state(self) -> ServerState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = self.get_named_state(name=ServerState.DEFAULT)
        # Default -> Connecting
        state.add_transition(transition=builder.get_default_connecting_transition())
        return state

    def get_connecting_state(self) -> ServerState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = self.get_named_state(name=ServerState.CONNECTING)
        # Connecting -> Connected
        state.add_transition(transition=builder.get_connecting_connected_transition())
        # Connecting -> Error
        state.add_transition(transition=builder.get_connecting_error_transition())
        return state

    def get_connected_state(self) -> ServerState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = self.get_named_state(name=ServerState.CONNECTED)
        # Connected -> Handshaking
        state.add_transition(transition=builder.get_connected_handshaking_transition())
        # Connected -> Error
        state.add_transition(transition=builder.get_connected_error_transition())
        return state

    def get_handshaking_state(self) -> ServerState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = self.get_named_state(name=ServerState.HANDSHAKING)
        # Handshaking -> Running
        state.add_transition(transition=builder.get_handshaking_running_transition())
        # Handshaking -> Connected
        state.add_transition(transition=builder.get_handshaking_connected_transition())
        # Handshaking -> Error
        state.add_transition(transition=builder.get_handshaking_error_transition())
        return state

    def get_running_state(self) -> ServerState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = self.get_named_state(name=ServerState.RUNNING)
        # Running -> Default
        state.add_transition(transition=builder.get_running_default_transition())
        # Running -> Error
        state.add_transition(transition=builder.get_running_error_transition())
        return state

    def get_error_state(self) -> ServerState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = self.get_named_state(name=ServerState.ERROR)
        # Error -> Default
        state.add_transition(transition=builder.get_error_default_transition())
        return state


class TransitionBuilder:

    # noinspection PyMethodMayBeStatic
    def get_default_connecting_transition(self):
        return DefaultConnectingTransition(target=ServerState.CONNECTING)

    # Connecting

    # noinspection PyMethodMayBeStatic
    def get_connecting_connected_transition(self):
        return ConnectingConnectedTransition(target=ServerState.CONNECTED)

    # noinspection PyMethodMayBeStatic
    def get_connecting_error_transition(self):
        return ConnectingErrorTransition(target=ServerState.ERROR)

    # Connected

    # noinspection PyMethodMayBeStatic
    def get_connected_handshaking_transition(self):
        return ConnectedHandshakingTransition(target=ServerState.HANDSHAKING)

    # noinspection PyMethodMayBeStatic
    def get_connected_error_transition(self):
        return ConnectedErrorTransition(target=ServerState.ERROR)

    # Handshaking

    # noinspection PyMethodMayBeStatic
    def get_handshaking_running_transition(self):
        return HandshakingRunningTransition(target=ServerState.RUNNING)

    # noinspection PyMethodMayBeStatic
    def get_handshaking_connected_transition(self):
        return HandshakingConnectedTransition(target=ServerState.CONNECTED)

    # noinspection PyMethodMayBeStatic
    def get_handshaking_error_transition(self):
        return HandshakingErrorTransition(target=ServerState.ERROR)

    # Running

    # noinspection PyMethodMayBeStatic
    def get_running_default_transition(self):
        return RunningDefaultTransition(target=ServerState.DEFAULT)

    # noinspection PyMethodMayBeStatic
    def get_running_error_transition(self):
        return RunningErrorTransition(target=ServerState.ERROR)

    # Error

    # noinspection PyMethodMayBeStatic
    def get_error_default_transition(self):
        return ErrorDefaultTransition(target=ServerState.DEFAULT)


#
#   Transitions
#

class DefaultConnectingTransition(StateTransition):
    """ Default -> Connecting """

    def evaluate(self, ctx: StateMachine) -> bool:
        if ctx.current_user is None:
            return False
        status = ctx.status
        return status == GateStatus.PREPARING or status == GateStatus.READY


class ConnectingConnectedTransition(StateTransition):
    """ Connecting -> Connected """

    def evaluate(self, ctx: StateMachine) -> bool:
        assert ctx.current_user is not None, 'server/user error'
        return ctx.status == GateStatus.READY


class ConnectingErrorTransition(StateTransition):
    """ Connecting -> Error """

    def evaluate(self, ctx: StateMachine) -> bool:
        return ctx.status == GateStatus.ERROR


class ConnectedHandshakingTransition(StateTransition):
    """ Connected -> Handshaking """

    def evaluate(self, ctx: StateMachine) -> bool:
        return ctx.current_user is not None


class ConnectedErrorTransition(StateTransition):
    """ Connected -> Error """

    def evaluate(self, ctx: StateMachine) -> bool:
        return ctx.status == GateStatus.ERROR


class HandshakingRunningTransition(StateTransition):
    """ Handshaking -> Running """

    def evaluate(self, ctx: StateMachine) -> bool:
        # when current user changed, the server will clear this session, so
        # if it's set again, it means handshake accepted
        return ctx.session_key is not None


class HandshakingConnectedTransition(StateTransition):
    """ Handshaking -> Connected """

    def evaluate(self, ctx: StateMachine) -> bool:
        state = ctx.current_state
        assert isinstance(state, ServerState)
        enter_time = state.enter_time
        if enter_time == 0:
            # not enter yet
            return False
        expired = enter_time + 30
        now = int(time.time())
        if now < expired:
            # not expired yet
            return False
        # handshake expired, return to connect to do it again
        return ctx.status == GateStatus.READY


class HandshakingErrorTransition(StateTransition):
    """ Handshaking -> Error """

    def evaluate(self, ctx: StateMachine) -> bool:
        return ctx.status == GateStatus.ERROR


class RunningDefaultTransition(StateTransition):
    """ Running -> Default """

    def evaluate(self, ctx: StateMachine) -> bool:
        # user switched?
        return ctx.session_key is None


class RunningErrorTransition(StateTransition):
    """ Running -> Error """

    def evaluate(self, ctx: StateMachine) -> bool:
        return ctx.status == GateStatus.ERROR


class ErrorDefaultTransition(StateTransition):
    """ Error -> Default """

    def evaluate(self, ctx: StateMachine) -> bool:
        return ctx.status != GateStatus.ERROR
