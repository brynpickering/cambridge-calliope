"""
Copyright (C) 2018 Bryn Pickering.
Licensed under the MIT License (see LICENSE file).
"""

import numpy as np
import pandas as pd


# Implement scenario reduction
def get_reduced_scenarios(costs, scenarios, probabilities=None):
    """
    Reduce the number of scenarios used to describe a uncertain parameter by
    minimising the Kantorovich distance for a number of desired reduced scenarios

    Parameters
    ----------
    costs : list
        Array of magintudes related to the scenarios.
        Ideally, objective function value from a simplified LP optimisation would
        give the magnitudes (and are thus monetary costs associated with that scenario).
    scenarios : int
        Number of reduced scenarios to pick.
    probabilities : list, default = None
        Array of probabilities of occurance for each scenario in the original set.
        If `None`, scenarios are assumed to be equiprobable.

    Returns
    -------
    chosen_scenarios : list
        list of scenarios chosen to reduce total Kantorovich distances.
        Scenario number refers to index of scenario given in `costs`

    """
    nu_1 = pd.DataFrame(np.repeat(costs, len(costs))
                        .reshape(-1, len(costs))).sub(costs, axis=1).abs()
    nu_1.index = [i for i in range(len(costs))]
    nu_1.columns = [i for i in range(len(costs))]
    chosen_scenarios = []

    # Get kantorovich distances for each scenario, which involves summing the cost function columnwise
    if probabilities:
        probabilities = pd.DataFrame(probabilities)
        d_1 = np.multiply(nu_1.T, probabilities).T.sum(axis=0)
    else:
        d_1 = nu_1.sum(axis=0)

    # Find column which has the lowest kantorovich distance. Column number = starting scenario
    # We may get multiple scenarios here (with same summed value), so we always take the first one
    s_1 = d_1[d_1 == d_1.min()].index[0]

    chosen_scenarios.append(s_1)
    nu_prev_i = nu_1
    for i in range(scenarios - 1):
        # Get the last loop's chosen scenario
        s_prev_i = chosen_scenarios[-1]

        # Remove the row and column associated with the previously chosen scenario
        nu_i = nu_prev_i.drop(s_prev_i, axis=1).drop(s_prev_i, axis=0)

        # Create a matrix where each row is the value of previously chosen scenario for that row
        min_matrix = nu_i.copy()
        for j in min_matrix.index:
            min_matrix.loc[j, :] = nu_prev_i.loc[j, s_prev_i]

        # In each row, set each element to be the minimum between it and the value of the
        # previously chosen scenario for that row
        nu_i = np.minimum(nu_i, min_matrix)

        # Get kantorovich distances for each scenario, which involves summing the cost function columnwise
        if probabilities is not None:
            probabilities = probabilities.drop(s_prev_i)
            d_i = np.multiply(nu_i.T, probabilities).T.sum(axis=0)
        else:
            d_i = nu_i.sum(axis=0)

        # Find column which has the lowest kantorovich distance. Column number = starting scenario
        # We may get multiple scenarios here (with same summed value), so we always take the first one
        s_i = d_i[d_i == d_i.min()].index[0]

        chosen_scenarios.append(s_i)
        # Latest matrix prepared to be the 'previous' matrix in the next iteration
        nu_prev_i = nu_i.copy()
    return chosen_scenarios


def get_redistributed_probabilities(costs, reduced_scenarios, probabilities=None):
    """
    Redistribute probabilities from a full set of samples to a subset of chosen
    reduced scenarios.

    Parameters
    ----------
    costs : list
        Array of magnitudes of the full sample set. Ideally, objective function
        value from a simplified LP optimisation would
        give the magnitudes (and are thus monetary costs associated with that sample).
    reduced_scenarios : list
        list of indeces from within `costs` that are the chosen reduced scenarios
    probabilities : list, default = None
        Array of probabilities of occurance for each scenario in the original set.
        If `None`, scenarios are assumed to be equiprobable

    Returns
    -------
    scenario_df : pandas DataFrame
        Dataframe with scenario number as index and scenario cost, reduced
        scenario to which probability is distributed,
        and redistributed probabilities as columns
    """

    scenario_df = pd.DataFrame(
        costs, columns=["cost"], index=[i for i in range(len(costs))]
    )
    reduced_costs = scenario_df.loc[reduced_scenarios, "cost"]
    unassigned_scenarios = scenario_df.drop(reduced_scenarios)
    scenario_df["reduced_scenario"] = np.nan
    scenario_df["probability"] = probabilities if probabilities else 1/len(costs)

    # Get closest reduced scenario for each scenario not chosen for the reduced set
    for i in unassigned_scenarios.index:
        scenario_df.loc[i, "reduced_scenario"] = (
            (reduced_costs - unassigned_scenarios.loc[i, "cost"])
            .abs().sort_values(inplace=False).index[0]
        )

    scenario_df.loc[reduced_scenarios, "reduced_scenario"] = reduced_scenarios

    # Redistribute probabilities. Unassigned scenarios "give" their probability
    # to their closest reduced set
    for i in reduced_scenarios:
        scenario_df.loc[i, 'probability'] = (
            scenario_df.loc[scenario_df.reduced_scenario == i]["probability"].sum()
        )
    scenario_df.loc[unassigned_scenarios.index, "probability"] = 0

    return scenario_df
