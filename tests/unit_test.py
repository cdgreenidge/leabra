import unittest
import copy

import numpy as np

import data

import dotdot  # pylint: disable=unused-import
import leabra



class UnitTestsAPI(unittest.TestCase):
    """Check that the Unit API behaves as expected."""

    def test_spec(self):
        """Test the behavior of spec"""
        u_spec = leabra.UnitSpec()
        u_spec.act_thr = 0.25
        u  = leabra.Unit(spec=u_spec) # by default, copyspec=False
        u2 = leabra.Unit(spec=u_spec)
        self.assertEqual(u.spec.act_thr, 0.25)
        self.assertEqual(u2.spec.act_thr, 0.25)
        u.spec.act_thr = 0.30
        self.assertEqual(u.spec.act_thr, 0.30)
        self.assertEqual(u2.spec.act_thr, 0.30)

        u3 = leabra.Unit(spec=u_spec.copy()) # u3 has an independent spec
        u3.spec.act_thr = 0.45
        self.assertEqual(u2.spec.act_thr, 0.30)
        self.assertEqual(u3.spec.act_thr, 0.45)

    def test_forced_act(self):
        """Test that forcing activity behaves as expected"""
        u = leabra.Unit()
        u.force_activity(0.5)
        u.calculate_net_in()
        u.cycle()
        self.assertEqual(u.act, 0.5)

        # is it maintained without call to add_excitatory() ?
        for _ in range(10):
            u.calculate_net_in()
            u.cycle()
            self.assertEqual(u.act, 0.5)

        u.add_excitatory(0.5)
        u.calculate_net_in()
        u.cycle()
        self.assertFalse(u.act == 0.5)


class UnitTestsBehavior(unittest.TestCase):
    """Check that the Unit behaves as they should.

    The checks are concerned with consistency with the equations that define the
    unit's behavior. These test should pass on the emergent implementation as
    well.
    """

    def test_act(self):
        """Test that the unit activity is behaving well under excitation."""

        spec = leabra.UnitSpec(g_bar_e=0.40, g_bar_l=2.80, g_bar_i=1.00,
                               e_rev_e=1.00, e_rev_l=0.15, e_rev_i=0.15,
                               g_l=1.0, act_thr=0.25, act_gain=600.00)
        u = leabra.Unit(spec=spec)

        for _ in range(15):
            u.add_excitatory(1.0)
            u.calculate_net_in()
            u.cycle()

        for _ in range(150):
            u.add_excitatory(1.0)
            u.calculate_net_in()
            u.cycle()
            self.assertTrue(0.85 < u.act <= 0.95)

        for _ in range(10):
            u.add_excitatory(0.0)
            u.calculate_net_in()
            u.cycle()

        self.assertTrue(u.act < 0.05)


    def test_xx1_thr(self):
        """Test the threshold for xx1 functions"""
        u_spec = leabra.UnitSpec()
        u_spec.act_thr = 0.25
        u = leabra.Unit(spec=u_spec)
        self.assertEqual(u_spec.xx1(-0.1), 0.0)
        self.assertTrue(0.0 < u_spec.xx1(0.1))
        self.assertEqual(u_spec.noisy_xx1(-0.1), 0.0)
        self.assertTrue(0.1 < u_spec.noisy_xx1(0.1))


    def test_avgs_forced(self):
        """Test if units with forced activity update their averages"""
        u = leabra.Unit()

        for t in range(10):
            u.force_activity(1.0)
            u.calculate_net_in()
            u.cycle()

        for name in ['avg_ss', 'avg_s', 'avg_m', 'avg_s_eff']:
            self.assertTrue(getattr(u, name) != 0.15)


    def test_emergent_xx1(self):
        """Test quantitative equivalence with emergent on the xx1 function."""
        xx1_data = data.parse_xy('convolve_nxx1.txt')

        spec = leabra.UnitSpec(adapt_on=False, noisy_act=True)
        receiver = leabra.Unit(spec=spec)
        receiver.cycle() # create the noisy_xx1 convolution

        xs, ys = spec._nxx1_conv

        check = True
        for k, (pys, ems) in enumerate([(xs, xx1_data['x']), (ys, xx1_data['y'])]):
            for t, (py, em) in enumerate(zip(pys, ems)):
                if not np.allclose(py, em, rtol=1e-05, atol=1e-08):
                    print('{}:{} [py] {:.10f} != {:.10f} [emergent]'.format('x' if k==0 else 'y', t, py, em))
                    check = False

        self.assertTrue(check)


    def test_emergent_neuron(self):
        """Test quantitative equivalence with emergent on the neuron tutorial."""
        for adapt_on in [False, True]:
            neuron_data = data.parse_unit('neuron_adapt.txt' if adapt_on else 'neuron.txt')

            spec = leabra.UnitSpec(adapt_on=adapt_on, noisy_act=True)
            log_names=('net', 'I_net', 'v_m', 'act', 'v_m_eq', 'adapt',
                       'avg_ss', 'avg_s', 'avg_m', 'avg_s_eff', 'avg_l')
            receiver = leabra.Unit(spec=spec, log_names=log_names)

            inputs = 10*[0.0] + 150*[1.0] + 40*[0.0]

            for g_e in inputs:
                receiver.add_excitatory(g_e)
                receiver.calculate_net_in()
                receiver.cycle()

            check = True
            for name in receiver.logs.keys():
                for t, (py, em) in enumerate(zip(receiver.logs[name], neuron_data[name])):
                    if not np.allclose(py, em, rtol=1e-05, atol=1e-07):
                        print('{}:{} [py] {:.10f} != {:.10f} [emergent] ({}adapt)'.format(
                               name, t,   py,        em,                 '' if adapt_on else 'no '))
                        check = False

            self.assertTrue(check)


if __name__ == '__main__':
    unittest.main()
