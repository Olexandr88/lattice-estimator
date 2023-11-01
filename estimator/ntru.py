# -*- coding: utf-8 -*-
"""
High-level NTRU interface
"""

from functools import partial
from sage.all import oo

from .ntru_primal import primal_dsd, primal_usvp, primal_bdd, primal_hybrid
from .lwe_bkw import coded_bkw # noqa
from .lwe_guess import exhaustive_search, mitm, distinguish, guess_composition # noqa
from .lwe_dual import dual, dual_hybrid # noqa
from .gb import arora_gb  # noqa
from .ntru_parameters import NTRUParameters as Parameters  # noqa
from .conf import (red_cost_model as red_cost_model_default,
                   red_shape_model as red_shape_model_default)
from .util import batch_estimate, f_name
from .reduction import RC


class Estimate:

    def rough(self, params, jobs=1, catch_exceptions=True):
        """
        This function makes the following somewhat routine assumptions:

        - The ZGSA holds.
        - The Core-SVP model holds.

        This function furthermore assumes the following heuristics:

        - The primal hybrid attack only applies to sparse secrets.
        - The dual hybrid MITM attack only applies to sparse secrets.
        - The dense sublattice attack only applies to possibly overstretched parameters

        :param params: NTRU parameters.
        :param jobs: Use multiple threads in parallel.
        :param catch_exceptions: When an estimate fails, just print a warning.

        EXAMPLE ::

            >>> from estimator import *
            >>> _ = NTRU.estimate.rough(schemes.NTRUHPS2048509Enc)
            usvp                 :: rop: ≈2^109.2, red: ≈2^109.2, δ: 1.004171, β: 374, d: 643, tag: usvp

        """
        params = params.normalize()

        algorithms = {}

        # Only primal attacks apply to NTRU
        algorithms["usvp"] = partial(primal_usvp, red_cost_model=RC.ADPS16, red_shape_model="zgsa")

        if params.possibly_overstretched:
            algorithms["dsd"] = partial(
                primal_dsd, red_cost_model=RC.ADPS16, red_shape_model="zgsa"
            )

        if params.Xs.is_sparse:
            algorithms["hybrid"] = partial(
                primal_hybrid, red_cost_model=RC.ADPS16, red_shape_model="zgsa"
            )

        res_raw = batch_estimate(
            params, algorithms.values(), log_level=1, jobs=jobs, catch_exceptions=catch_exceptions
        )
        res_raw = res_raw[params]
        res = {
            algorithm: v for algorithm, attack in algorithms.items()
            for k, v in res_raw.items()
            if f_name(attack) == k
        }

        for algorithm in algorithms:
            if algorithm not in res:
                continue
            result = res[algorithm]
            if result["rop"] != oo:
                print(f"{algorithm:20s} :: {result!r}")

        return res

    def __call__(
        self,
        params,
        red_cost_model=red_cost_model_default,
        red_shape_model=red_shape_model_default,
        deny_list=tuple(),
        add_list=tuple(),
        jobs=1,
        catch_exceptions=True,
    ):
        """
        Run all estimates.

        :param params: NTRU parameters.
        :param red_cost_model: How to cost lattice reduction.
        :param red_shape_model: How to model the shape of a reduced basis (applies to primal attacks)
        :param deny_list: skip these algorithms
        :param add_list: add these ``(name, function)`` pairs to the list of algorithms to estimate.a
        :param jobs: Use multiple threads in parallel.
        :param catch_exceptions: When an estimate fails, just print a warning.

        EXAMPLE ::

            >>> from estimator import *
            >>> _ = NTRU.estimate(schemes.NTRUHPS2048509Enc)
            usvp                 :: rop: ≈2^134.5, red: ≈2^134.5, δ: 1.004179, β: 373, d: 923, tag: usvp
            bdd                  :: rop: ≈2^130.9, red: ≈2^129.9, svp: ≈2^129.9, β: 356, η: 389, d: 917, tag: bdd
            bdd_hybrid           :: rop: ≈2^130.9, red: ≈2^129.9, svp: ≈2^129.9, β: 356, η: 389, ζ: 0, |S|: 1, ...
            bdd_mitm_hybrid      :: rop: ≈2^185.3, red: ≈2^184.5, svp: ≈2^184.2, β: 371, η: 2, ζ: 159, |S|: ≈2^228.0...

            >>> params = NTRU.Parameters(n=113, q=512, Xs=ND.UniformMod(3), Xe=ND.UniformMod(3))
            >>> _ = NTRU.estimate(params)
            usvp                 :: rop: ≈2^46.0, red: ≈2^46.0, δ: 1.011516, β: 59, d: 221, tag: usvp
            dsd                  :: rop: ≈2^37.9, red: ≈2^37.9, δ: 1.013310, β: 31, d: 226, tag: dsd
            bdd                  :: rop: ≈2^42.4, red: ≈2^41.0, svp: ≈2^41.8, β: 41, η: 70, d: 225, tag: bdd
            bdd_hybrid           :: rop: ≈2^42.4, red: ≈2^41.0, svp: ≈2^41.8, β: 41, η: 70, ζ: 0, |S|: 1, d: 226, ...
            bdd_mitm_hybrid      :: rop: ≈2^55.6, red: ≈2^54.7, svp: ≈2^54.6, β: 41, η: 2, ζ: 32, |S|: ≈2^50.7, ...
        """
        params = params.normalize()

        algorithms = {}

        algorithms["usvp"] = partial(
            primal_usvp, red_cost_model=red_cost_model, red_shape_model=red_shape_model
        )
        algorithms["dsd"] = partial(
            primal_dsd, red_cost_model=red_cost_model, red_shape_model=red_shape_model
        )

        algorithms["bdd"] = partial(
            primal_bdd, red_cost_model=red_cost_model, red_shape_model=red_shape_model
        )
        algorithms["bdd_hybrid"] = partial(
            primal_hybrid,
            mitm=False,
            babai=False,
            red_cost_model=red_cost_model,
            red_shape_model=red_shape_model,
        )
        # we ignore the case of mitm=True babai=False for now, due to it being overly-optimistic
        algorithms["bdd_mitm_hybrid"] = partial(
            primal_hybrid,
            mitm=True,
            babai=True,
            red_cost_model=red_cost_model,
            red_shape_model=red_shape_model,
        )

        algorithms = {k: v for k, v in algorithms.items() if k not in deny_list}
        algorithms.update(add_list)

        res_raw = batch_estimate(
            params, algorithms.values(), log_level=1, jobs=jobs, catch_exceptions=catch_exceptions
        )
        res_raw = res_raw[params]
        res = {
            algorithm: v
            for algorithm, attack in algorithms.items()
            for k, v in res_raw.items()
            if f_name(attack) == k
        }
        for algorithm in algorithms:
            if algorithm not in res:
                continue
            result = res[algorithm]
            if result["rop"] == oo:
                continue
            if algorithm == "hybrid" and res["bdd"]["rop"] < result["rop"]:
                continue
            if algorithm == "dsd" and res["usvp"]["rop"] < result["rop"]:
                continue
            print(f"{algorithm:20s} :: {result!r}")

        return res


estimate = Estimate()
