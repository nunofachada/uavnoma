"""
    This script performs a simulation of a UAV-NOMA system with two users.
"""

import argparse
import numpy as np
import pandas as pd
import tabulate as tab
import matplotlib.pyplot as plt
import uavnoma

def main():

    # Create an argument parser
    parser = argparse.ArgumentParser(description='Model of UAV-NOMA system with two users.',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Specify arguments to parse
    parser.add_argument('-s', '--monte-carlo-samples', type=int, metavar='SAMPLES',
                        help='Monte Carlo samples', default=10000)
    parser.add_argument('-p', '--power-los', type=float, metavar='POWER_LOS',
                        help='Power of line-of-sight path and scattered paths, 1 <= POWER_LOS <= 2',
                        default=1.0)
    parser.add_argument('-f', '--rician-factor', type=int, metavar='FACTOR',
                        help='Rician factor value, 10<= FACTOR <= 15',
                        default=15)
    parser.add_argument('-l', '--path-loss', type=float, metavar='LOSS',
                        help='Path loss exponent, 2 <= LOSS <= 3',
                        default=2.2)
    parser.add_argument('-r', '--radius-uav', type=float, metavar='RADIUS',
                        help='Radius fly trajectory of the UAV in meters',
                        default=2.0)
    parser.add_argument('-u', '--radius-user', type=float, metavar='RADIUS',
                        help='Distribution radius of users in the cell in meters',
                        default=10.0)
    parser.add_argument('-m', '--uav-height-mean', type=float, metavar='MEAN',
                        help='Average UAV flight height',
                        default=15.0)
    parser.add_argument('-t1', '--target-rate-primary-user', type=float, metavar='RATE',
                        help='Target rate bits/s/Hertz  primary user',
                        default=0.5)
    parser.add_argument('-t2', '--target-rate-secondary-user', type=float, metavar='RATE',
                        help='Target rate bits/s/Hertz  secondary user',
                        default=0.5)
    parser.add_argument('-hi', '--hardw-ip', type=float, metavar='COEFF',
                        help='Residual Hardware Impairments coefficient, 0 <= COEFF <=1',
                        default=0.0)
    parser.add_argument('-si', '--sic-ip', type=float, metavar='COEFF',
                        help='Residual Imperfect SIC coefficient, 0 <= COEFF <=1',
                        default=0.0)
    parser.add_argument('-p1', '--power-coeff-primary', type=float, metavar='COEFF',
                        help='The value of power coefficient allocation of the Primary User',
                        default=0.8)
    parser.add_argument('-p2', '--power-coeff-secondary', type=float, metavar='COEFF',
                        help='The value of power coefficient allocation of the Secondary User',
                        default=0.2)
    parser.add_argument('--snr-min', type=float, metavar='SNR_MIN',
                        help='Minimum / starting SNR in dB',
                        default=10)
    parser.add_argument('--snr-max', type=float, metavar='SNR_MAX',
                        help='Maximum / finishing SNR in dB',
                        default=60)
    parser.add_argument('--snr-samples', type=int, metavar='NUM',
                        help='Number of SNR samples between SNR_MIN and SNR_MAX',
                        default=26)
    parser.add_argument('--seed', type=int, metavar="SEED",
                        help="Seed for pseudo-random number generator",
                        default = None)
    parser.add_argument('-o', '--output', type=str, metavar='FILE',
                        help='CSV file where to save simulation data',
                        default=None)
    parser.add_argument('--plot', action='store_true',
                        help='Plot the values of the achievable rate and outage probability',
                        default=False)
    parser.add_argument('--no-print', action='store_true',
                        help='Do not print results to terminal',
                        default=False)

    # Unused arguments for now
    parser.add_argument('--number-uav', type=int, metavar='NUM',
                        help=argparse.SUPPRESS, # 'Number of UAV must be 1',
                        default=1)
    parser.add_argument('--number-user', type=int, metavar='NUM',
                        help=argparse.SUPPRESS, # 'Number of users must be 2',
                        default=2)

    # Parse command line arguments
    args = parser.parse_args()

    # If a seed was defined, set it
    if (args.seed != None):
        np.random.seed(args.seed)

    # Initialization of some auxiliary arrays
    snr_dB = np.linspace(args.snr_min, args.snr_max, args.snr_samples) # SNR in dB
    snr_linear = 10.0 ** (snr_dB / 10.0)  # SNR linear
    out_probability_system = np.zeros((args.monte_carlo_samples, len(snr_dB)))
    out_probability_secondary_user = np.zeros((args.monte_carlo_samples, len(snr_dB)))
    out_probability_primary_user = np.zeros((args.monte_carlo_samples, len(snr_dB)))
    system_average_rate = np.zeros((args.monte_carlo_samples, len(snr_dB)))
    rate_secondary_user = np.zeros((args.monte_carlo_samples, len(snr_dB)))
    rate_primary_user = np.zeros((args.monte_carlo_samples, len(snr_dB)))


    # ------------------------------------------------------------------------------------
    # Fixed power allocation
    #power_coeff_primary = float(input('Enter the value of power coefficient allocation of the Primary User: '))
    #power_coeff_secondary = 1 - power_coeff_primary
    assert (
        args.power_coeff_primary >= args.power_coeff_secondary
    ),  "The power coefficient of the primary user must be greater than that of the Secondary user."

    sum_power = args.power_coeff_primary + args.power_coeff_secondary
    assert (sum_power > 0) and (
        sum_power <= 1
    ) , "The sum of the powers must be > 0 or <= 1."


    for mc in range(args.monte_carlo_samples):
        # Position UAV and users
        uav_axis_x, uav_axis_y, uav_height = uavnoma.random_position_uav(args.number_uav,
                                                                        args.radius_uav,
                                                                        args.uav_height_mean)

        user_axis_x, user_axis_y = uavnoma.random_position_users(args.number_user,
                                                                args.radius_user)

        s, sigma = uavnoma.fading_rician(args.rician_factor, args.power_los)

        # Generate channel gains
        channel_gain_primary, channel_gain_secondary =  uavnoma.generate_channel(
            s,
            sigma,
            args.number_user,
            user_axis_x,
            user_axis_y,
            uav_axis_x,
            uav_axis_y,
            uav_height,
            args.path_loss,
        )

        # Analyzes system performance metrics for various SNR values
        for sn in range(0, len(snr_dB)):

            # Calculating achievable rate of primary user
            rate_primary_user[mc, sn] = uavnoma.calculate_instantaneous_rate_primary(
                channel_gain_primary,
                snr_linear[sn],
                args.power_coeff_primary,
                args.power_coeff_secondary,
                args.hardw_ip,
            )
            # Calculating achievable rate of secondary user
            rate_secondary_user[mc, sn] = uavnoma.calculate_instantaneous_rate_secondary(
                channel_gain_secondary,
                snr_linear[sn],
                args.power_coeff_secondary,
                args.power_coeff_primary,
                args.hardw_ip,
                args.sic_ip,
            )

            system_average_rate[mc, sn] = uavnoma.average_rate(rate_primary_user[mc, sn],
                                                            rate_secondary_user[mc, sn])

            # Calculating of outage probability of the system
            out_probability_system[mc, sn], out_probability_primary_user[mc,sn], out_probability_secondary_user[mc, sn] = uavnoma.outage_probability(
                rate_primary_user[mc, sn],
                rate_secondary_user[mc, sn],
                args.target_rate_primary_user,
                args.target_rate_secondary_user,
            )

    ## Outage Probability

    # Outage probability of the System
    out_prob_mean = np.mean(out_probability_system, axis=0)

    # Outage probability of the Primary User
    out_prob_primary = np.mean(out_probability_primary_user, axis=0)

    # Outage probability of the Secondary User
    out_prob_secondary = np.mean(out_probability_secondary_user, axis=0)

    ## Achievable Rate

    # Average achievable rate of the system
    average_rate_mean = np.mean(system_average_rate, axis=0)

    # Average achievable rate of the Primary User
    rate_mean_primary_user = np.mean(rate_primary_user, axis=0)

    # Average achievable rate of the Secondary User
    rate_mean_secondary_user = np.mean(rate_secondary_user, axis=0)


    # Put all mean data into a numpy matrix / table
    all_data_np = np.c_[ snr_dB, out_prob_mean, out_prob_primary, out_prob_secondary,
                        average_rate_mean, rate_mean_primary_user, rate_mean_secondary_user]

    # Convert numpy matrix to Pandas dataframe with column names
    all_data_df = pd.DataFrame(all_data_np,
                            columns = ['snr_DB', 'p_outage_sys', 'p_outage_usr1',
                                        'p_outage_usr2', 'avg_arate_sys',
                                        'avg_arate_usr1', 'avg_arate_usr2' ])

    # Print to screen, except if --no-print option was specified
    if not args.no_print:
        print(tab.tabulate(all_data_df, tablefmt='psql', showindex=False,
                        headers=['SNR\n(dB)', 'Outage\nprobability\nSystem',
                                    'Outage\nprobability\nPrimary user',
                                    'Outage\nprobability\nSecondary user',
                                    'Average\nachievable rate\nSystem',
                                    'Average\nachievable rate\nPrimary User',
                                    'Average\nachievable rate\nSecondary User']))

    # Save results to file if a filename was specified
    if args.output != None:
        all_data_df.to_csv(args.output, index=False)

    # Plot simulation results if --plot option was given
    if args.plot:

        # Outage probability
        plt.semilogy(snr_dB, out_prob_primary, "b.-", label="Primary user", linewidth=1)
        plt.semilogy(snr_dB, out_prob_secondary, "r.-", label="Secondary user", linewidth=1)
        plt.xlabel("SNR (dB)")
        plt.ylabel("Outage Probability")
        plt.legend(loc="lower left")

        # Determine the highest index of the outage probability arrays containing values > 0
        i_max = len(snr_dB) - 1
        for i in range(len(snr_dB) - 1, 0, -1):
            if out_prob_primary[i] == 0 and out_prob_secondary[i] == 0:
                i_max = i
            else:
                break

        # Adjust plot
        plt.xlim(args.snr_min, snr_dB[i_max])

        # Average Achievable Rate of the users
        plt.figure()
        plt.plot(snr_dB, rate_mean_primary_user, "b.-", label="primary user", linewidth=1)
        plt.plot(snr_dB, rate_mean_secondary_user, "r.-", label="secondary user", linewidth=1)
        plt.xlabel("SNR (dB)")
        plt.ylabel("Achievable rate (bits/s/Hz)")
        plt.legend(loc="upper left")
        plt.xlim(args.snr_min, args.snr_max)

        plt.show()
