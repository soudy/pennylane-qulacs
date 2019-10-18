import numpy as np

from pennylane import Device

from qulacs import Observable, QuantumCircuit, QuantumState
from qulacs.gate import CNOT, RX, RY, RZ, X, Y, Z, U3, DenseMatrix
from qulacs.state import inner_product


X_matrix = np.array([[0, 1], [1, 0]])
Y_matrix = np.array([[0, -1j], [1j, 0]])
Z_matrix = np.array([[1, 0], [0, -1]])
H_matrix = np.array([[1, 1], [1, -1]])/np.sqrt(2)


def hermitian(*args):
    r"""Input validation for an arbitary Hermitian expectation.
    Args:
        args (array): square hermitian matrix
    Returns:
        array: square hermitian matrix
    """
    A = np.asarray(args[0])

    if A.shape[0] != A.shape[1]:
        raise ValueError('Expectation must be a square matrix.')

    if not np.allclose(A, A.conj().T):
        raise ValueError('Expectation must be Hermitian.')

    return A


class QulacsDevice(Device):
    """Qulacs device"""
    name = 'Qulacs device'
    short_name = 'qulacs.simulator'
    pennylane_requires = '>=0.5.0'
    version = '0.0.1'
    author = 'Steven Oud'

    operations = {'CNOT', 'RX', 'RY', 'RZ', 'Rot', 'QubitStateVector',
            'PauliX', 'PauliY', 'PauliZ'}
    observables = {'PauliX', 'PauliY', 'PauliZ', 'Hermitian'}

    _observable_map = {
        'PauliX': X_matrix,
        'PauliY': Y_matrix,
        'PauliZ': Z_matrix,
        'Hadamard': H_matrix,
        'Hermitian': hermitian
    }

    def __init__(self, wires, **kwargs):
        super().__init__(wires=wires)

        self._state = QuantumState(wires)
        self._circuit = QuantumCircuit(wires)

    def apply(self, operation, wires, par):
        if operation == 'QubitStateVector':
            if len(par[0]) != 2**len(wires):
                raise ValueError('State vector must be of length 2**wires.')
            self._state.load(par[0])
            return

        if operation == 'CNOT':
            self._circuit.add_gate(CNOT(*wires))
        elif operation == 'Rot':
            self._circuit.add_gate(U3(wires[0], *par))
        elif operation == 'RX':
            self._circuit.add_gate(RX(wires[0], par[0]))
        elif operation == 'RY':
            self._circuit.add_gate(RY(wires[0], par[0]))
        elif operation == 'RZ':
            self._circuit.add_gate(RZ(wires[0], par[0]))
        elif operation == 'PauliX':
            self._circuit.add_gate(X(wires[0]))
        elif operation == 'PauliY':
            self._circuit.add_gate(Y(wires[0]))
        elif operation == 'PauliZ':
            self._circuit.add_gate(Z(wires[0]))
        else:
            raise ValueError(f'Invalid operation "{operation}"')

    @property
    def state(self):
        state = self._state.get_vector()

        return state.reshape([2] * self.num_wires).T.flatten()

    def pre_measure(self):
        self._circuit.update_quantum_state(self._state)

    def expval(self, observable, wires, par):
        bra = self._state.copy()

        A = self._get_operator_matrix(observable, par)
        dense_gate = DenseMatrix(wires, A)
        dense_gate.update_quantum_state(self._state)

        expectation = inner_product(bra, self._state)

        return expectation.real

    def reset(self):
        self._state = QuantumState(self.num_wires)
        self._state.set_zero_state()
        self._circuit = QuantumCircuit(self.num_wires)

    def _get_operator_matrix(self, operation, par):
        A = self._observable_map[operation]
        if not callable(A):
            return A

        return A(*par)