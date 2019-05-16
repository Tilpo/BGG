# -*- coding: utf8 -*-

from collections import Counter
from sympy.utilities.iterables import subsets
from sage.modules.with_basis.indexed_element import IndexedFreeModuleElement
from sage.combinat.free_module import CombinatorialFreeModule
from sage.sets.finite_enumerated_set import FiniteEnumeratedSet
from sage.rings.rational_field import RationalField


class LieAlgebraModuleElement(IndexedFreeModuleElement):
    """Element class of LieAlgebraModule. We only modify __repr__ here for clear display"""

    def __init__(self, parent, x):
        super(LieAlgebraModuleElement, self).__init__(parent, x)

    def __repr__(self):
        if len(self.monomials()) == 0:
            return '0'
        output_string = ''

        # display all the monomials+coefficients as a sum, omiting + if there is a minus in the next term,
        # and omitting the coefficient if it is 1.
        for t, c in self.monomial_coefficients().items():
            if len(output_string) > 0:
                try:
                    if c < 0:
                        output_string += '-'
                        c *= -1
                    else:
                        output_string += '+'
                except:
                    output_string += '+'
            if c not in {1, -1}:
                output_string += str(c) + '*'
            output_string += str(t)
        return output_string


class LieAlgebraModule(CombinatorialFreeModule):
    """Class for working with Lie algebra modules (with basis). This class is designed to work well with modules over
    a Lie algebra G which are formed by the following pieces:
    - The Lie algebra G with (co)adjoint action
    - The positive/negative parts in the Chevallay basis plus the maximal torus, again with (co)adjoint action
    With operations, direct sum, tensor products, symmetric powers, exterior powers and quotients by submodules."""

    Element = LieAlgebraModuleElement

    @staticmethod
    def __classcall_private__(cls, base_ring, basis_keys, lie_algebra, action, *options):
        if isinstance(basis_keys, (list, tuple)):
            basis_keys = FiniteEnumeratedSet(basis_keys)
        return super(LieAlgebraModule, cls).__classcall__(cls, base_ring, basis_keys, lie_algebra, action, *options)

    def __init__(self, base_ring, basis_keys, lie_algebra, action):
        self.lie_algebra = lie_algebra
        self._index_action = action
        self.basis_keys = basis_keys
        super(LieAlgebraModule, self).__init__(base_ring, basis_keys=basis_keys)

    def action(self, X, m):
        """self._index_action(X,m) produces a dictionary encoding the action on a basis element. This function
        uses self._index_action to extend to define the action of X on m, resulting in an element X.m in the
        module."""

        assert isinstance(X, self.lie_algebra.element_class)
        assert isinstance(m, self.element_class)
        total = self.zero()
        for i, c in m.monomial_coefficients().iteritems():
            total += c * sum([d * self.basis()[j] for j, d in self._index_action(X, i).items()],
                             self.zero())
        return total

    def direct_sum(*modules):
        """Given a list of modules, produces a new module encoding the direct sum of these modules. The basis is the
        join of the bases of the modules. We use the class DirectSum() to keep track of which basis elements belongs
        to which original module. The action on the direct sum of modules is defined by the restriction on the original
        modules on each module."""

        new_basis = []
        actions = dict()
        for i, module in enumerate(modules):
            new_basis += [DirectSum(i, key) for key in module.basis_keys]
            actions[i] = module._index_action

        def action(X, m):
            return direct_sum_map(m.index, actions[m.index](X, m.key))

        return LieAlgebraModule(modules[0].base_ring(), new_basis, modules[0].lie_algebra, action)

    def tensor_product(*modules):
        """Gives the tensor product of the modules. The basis is given by the set of all tuples, such that each
        element in the tuple belongs to precisely one of the original modules. The action is defined through
        the coproduct, e.g. X.(a (x) b) = (X.a)(x)b+a(x)(X.b)."""

        new_basis = LieAlgebraModule.tensor_product_basis(*[module.basis_keys for module in modules])

        def action(X, m):
            out_dict = Counter()
            for index, key in enumerate(m):
                action_on_term = modules[index]._index_action(X, key)
                index_dict = Counter({m.replace(index, t): c for t, c in action_on_term.items()})
                out_dict += index_dict
            return out_dict

        return LieAlgebraModule(modules[0].base_ring(), new_basis, modules[0].lie_algebra, action)

    def symmetric_power(self, n):
        """Gives n-fold symmetric power of module. The basis is given by the set of all sub-multisets (with repetition)
        of size n of the basis of the module. The action is induced from the action on the tensor product.
        In the special case that n=0, we return the module spanned by 0 elements. Technically we should return the
        base ring, but I first need to program the base ring as a Lie algebra module. For n==1 we return a fresh instance of the same LieAlgebraModule."""

        if n == 0:
            # technically this should return a copy of the base irng instead
            return LieAlgebraModule(self.base_ring(), [], self.lie_algebra, lambda X, k: {})
        if n == 1:
            return LieAlgebraModule(self.base_ring(), self.basis_keys, self.lie_algebra, self._index_action)

        new_basis = subsets(self.basis_keys, n, repetition=True)
        new_basis = [SymmetricProduct(*i) for i in new_basis]

        def action(self, X, m):
            out_dict = Counter()
            for index, key in enumerate(m):
                action_on_term = self._index_action(X, key)
                index_dict = Counter({m.replace(index, t): c for t, c in action_on_term.items()})
                out_dict += index_dict
            return out_dict

        return LieAlgebraModule(self.base_ring(), new_basis, self.lie_algebra, action)

    def alternating_power(self, n):
        """Gives n-fold symmetric power of module. The basis is given by the set of all subsets (without repetition)
        of size n of the basis of the module. The action is induced from the action on the tensor product. In the
        special case that n=0, we return the free module on zero generators. Technically we should return the base
        ring, but I first need to program the base ring as a Lie algebra module. For n==1 we return a fresh instance
        of the same LieAlgebraModule. If n is larger than the dimension of the module,we also return the free module
        on zero generators."""

        if n == 0:
            # technically this should return a copy of the base irng instead
            return LieAlgebraModule(self.base_ring(), [], self.lie_algebra, lambda X, k: {})
        if n == 1:
            return LieAlgebraModule(self.base_ring(), self.basis_keys, self.lie_algebra, self._index_action)
        if n > len(self.basis_keys):
            return LieAlgebraModule(self.base_ring(), [], self.lie_algebra, lambda X, k: {})

        new_basis = subsets(self.basis_keys, n, repetition=False)
        new_basis = [AlternatingProduct(*i) for i in new_basis]

        def action(X, m):
            out_dict = Counter()
            for index, key in enumerate(m):
                action_on_term = self._index_action(X, key)
                for t, c in action_on_term.items():
                    unsorted_term = m.replace(index, t)
                    parity = unsorted_term.parity()
                    if parity != 0:
                        out_dict[unsorted_term.sort()] += c * parity
            return out_dict

        return LieAlgebraModule(self.base_ring(), new_basis, self.lie_algebra, action)

    @staticmethod
    def _tensor_product_basis(*iterators):
        """gives the set of all (ordered) tuples of same length as number of iterators, where the ith element belongs to the
        ith iterator. """
        iterators = list(iterators)
        basis = [[x] for x in iterators.pop()]
        while len(iterators) > 0:
            iterator = iterators.pop()
            basis = [[x] + y for x in iterator for y in basis]
        basis = [TensorProduct(*b) for b in basis]
        return basis


class DirectSum:
    def __init__(self, index, key):
        self.index = int(index)
        self.key = key

    def __hash__(self):
        return hash((self.index, self.key))

    def __eq__(self, other):
        return (self.key, self.index) == (other.key, other.index)

    def __repr__(self):
        #return '(⊕%d, %s)' % (self.index, str(self.key))
        return str(self.key)


class TensorProduct:
    def __init__(self, *keys):
        self.keys = tuple(keys)

    def __hash__(self):
        return hash(self.keys)

    def __eq__(self, other):
        return self.keys == other.keys

    def __repr__(self):
        return '⊗'.join([str(k) for k in self.keys])

    def __getitem__(self, index):
        return self.keys[index]

    def __setitem__(self, index, value):
        keys = list(self.keys)
        keys[index] = value
        self.keys = tuple(keys)
        return self

    def replace(self, index, value):
        keys = list(self.keys)
        keys[index] = value
        return TensorProduct(*keys)


class SymmetricProduct:
    def __init__(self, *keys):
        self.keys = sorted(keys)

    def __hash__(self):
        return hash(tuple(self.keys))

    def __eq__(self, other):
        return self.keys == other.keys

    def __repr__(self):
        return '⊙'.join([str(k) for k in self.keys])

    def __getitem__(self, index):
        return self.keys[index]

    def __setitem__(self, index, value):
        self.keys[index] = value
        return self

    def replace(self, index, value):
        keys = self.keys
        keys[index] = value
        return SymmetricProduct(*keys)


class AlternatingProduct:
    def __init__(self, *keys):
        self.keys = list(keys)

    def __hash__(self):
        return hash(tuple(self.keys))

    def __eq__(self, other):
        return self.keys == other.keys

    def __repr__(self):
        return '∧'.join([str(k) for k in self.keys])

    def __getitem__(self, index):
        return self.keys[index]

    def __setitem__(self, index, value):
        self.keys[index] = value
        return self

    def replace(self, index, value):
        keys = list(self.keys)
        keys[index] = value
        return AlternatingProduct(*keys)

    def parity(self):
        """Computes the parity of the permutation. """
        a = list(self.keys)
        if len(set(a)) < len(a):
            return 0
        b = sorted(a)
        inversions = 0
        while a:
            first = a.pop(0)
            inversions += b.index(first)
            b.remove(first)
        return -1 if inversions % 2 else 1

    def sort(self):
        self.keys = sorted(self.keys)
        return self


def direct_sum_map(index, dic):
    return {DirectSum(index, k): v for k, v in dic.items()}


class LieAlgebraModuleFactory:
    def __init__(self, lie_algebra):
        self.lie_algebra = lie_algebra
        self.lattice = lie_algebra.weyl_group().domain().root_system.root_lattice()

        self.f_roots = list(self.lattice.negative_roots())
        self.e_roots = list(self.lattice.positive_roots())
        self.h_roots = self.lattice.alphacheck().values()

        self._initialize_root_dictionary()

        self.basis = dict()
        self.basis['g'] = sorted(self.string_to_root.keys())
        self.basis['u'] = sorted([self.root_to_string[r] for r in self.e_roots])
        self.basis['n'] = sorted([self.root_to_string[r] for r in self.f_roots])
        self.basis['b'] = sorted(self.basis['n'] + [self.root_to_string[r] for r in self.h_roots])

        self.subalgebra = dict()
        self.subalgebra['g'] = self.lie_algebra
        self.subalgebra['u'] = self._basis_to_subalgebra(self.basis['u'])
        self.subalgebra['n'] = self._basis_to_subalgebra(self.basis['n'])
        self.subalgebra['b'] = self._basis_to_subalgebra(self.basis['b'])

    def _initialize_root_dictionary(self):
        def root_dict_to_string(root_dict):
            return ''.join(''.join([str(k)] * abs(v)) for k, v in root_dict.items())

        self.string_to_root = dict( )
        for i, b in dict(self.lattice.alphacheck()).items():
            self.string_to_root['h%d' % i] = b
        for a in self.lattice.negative_roots():
            key = 'f' + root_dict_to_string(a.monomial_coefficients())
            self.string_to_root[key] = a
        for a in self.lattice.positive_roots():
            key = 'e' + root_dict_to_string(a.monomial_coefficients())
            self.string_to_root[key] = a

        self.root_to_string = {r: i for i, r in self.string_to_root.items()}

    def string_to_lie_algebra(self, m, subalgebra='g'):
        lie_algebra = self.subalgebra[subalgebra]
        return lie_algebra.basis()[self.string_to_root[m]]

    def _basis_to_subalgebra(self, basis):
        basis = [self.lie_algebra.basis()[self.string_to_root[r]] for r in basis]
        return self.lie_algebra.subalgebra(basis)

    def lie_alg_to_module_basis(self, X):
        """Takes an element of the Lie algebra and writes it out as a dict in the module basis"""
        out_dict = {}
        for t, c in X.monomial_coefficients().items():
            out_dict[self.root_to_string[t]] = c
        return out_dict

    def adjoint_action(self, X, m, subalgebra='g'):
        """Takes X and element of the Lie algebra, and m an index of the basis of the Lie algebra, and outputs
        the adjoint action of X on the corresponding basis element"""
        lie_algebra = self.subalgebra[subalgebra]
        bracket = lie_algebra.bracket(X, self.string_to_lie_algebra(m, subalgebra=subalgebra))
        return self.lie_alg_to_module_basis(bracket)

    def construct_module(self, base_ring=RationalField(), subalgebra='g', action='adjoint'):
        if action=='adjoint':
            action_map = lambda X, m: self.adjoint_action(X,m,subalgebra=subalgebra)
            return LieAlgebraModule(base_ring, self.basis[subalgebra], self.subalgebra[subalgebra], action_map)