import random
from logging import DEBUG
from typing import Sequence, Tuple, Union

import numpy as np

from sampleddetection.datastructures import Action, State
from sampleddetection.samplers import FeatureFactory, TSSampler
from sampleddetection.utils import clamp, setup_logger, within


class SamplingEnvironment:
    """
    Responsibilities:
        Basic sampling of environments using window length and window frequency.
    State is defined as:
        A point in time together with current window size and current frequency
    """

    # Hyperparameters
    # CHECK: That we hav good ranges
    WINDOW_SKIP_RANGE = [1e-7, 1e2]
    WINDOW_LENGTH_RANGE = [1e-6, 1e2]
    AMOUNT_OF_SAMPLES_PER_ACTION = 1  # Where action means selection of frequency/window
    PREVIOUS_AMNT_SAMPLES = 12
    DAY_RIGHT_MARGIN = 1  # CHECK: Must be equal 1 at deployment

    def __init__(
        self,
        sampler: TSSampler,
        feature_factory: FeatureFactory,
    ):

        self.sampler = sampler
        self.logger = setup_logger(self.__class__.__name__, DEBUG)
        # self.observable_features = observable_features
        self.feature_factory = feature_factory

        # Internal representation of State. Will be returned to viewer as in `class State` language
        self.starting_time = float("-inf")
        self.cur_winlen = float("-inf")
        self.cur_winskip = float("-inf")

    def step(self, action: Action) -> Tuple[State, float]:
        """
        returns
        ~~~~~~~
            State:  State
            Reward: float
        """
        status = [self.starting_time > 0, self.cur_winskip > 0, self.cur_winskip > 0]
        assert all(status), "Make sure you initialize enviornment properly"

        # Get current positions
        self.cur_winskip = clamp(
            self.cur_winskip + action.winskip_delta,
            self.WINDOW_SKIP_RANGE[0],
            self.WINDOW_SKIP_RANGE[1],
        )
        self.cur_winlen = clamp(
            self.cur_winlen + action.winlength_delta,
            self.WINDOW_LENGTH_RANGE[0],
            self.WINDOW_SKIP_RANGE[1],
        )
        return self._step(self.starting_time, self.cur_winskip, self.cur_winlen)

    def _step(self, starting_time, winskip, winlen) -> Tuple[State, float]:
        """
        returns
        ~~~~~~~
            State:  State
            Reward: float
        """
        # Do Sampling
        samples = self.sampler.sample(starting_time, winskip, winlen)

        arraylike_features = self.feature_factory.make_feature(samples)

        return_state = State(
            time_point=starting_time,
            window_skip=winskip,
            window_length=winlen,
            observations=arraylike_features,
            # observable_features=self.observable_features,
        )

        # TODO: calculatae the reward
        return_reward = 0

        return return_state, return_reward

    def reset(
        self,
        starting_time: Union[float, None] = None,
        winskip: Union[float, None] = None,
        winlen: Union[float, None] = None,
    ) -> State:
        # Find different simulatenous positions to draw from
        # Staring Frequencies
        # Create New Flow Session

        self._initialize_triad(starting_time, winskip, winlen)

        samples: Sequence = self.sampler.sample(
            self.starting_time,
            self.cur_winskip,
            self.cur_winlen,
        )

        self.logger.info(f"We get a sample that looks like")

        arraylike_features = self.feature_factory.make_feature(samples)

        return_state = State(
            time_point=self.starting_time,
            window_skip=self.cur_winskip,
            window_length=self.cur_winlen,
            observations=arraylike_features,
            # observable_features=self.observable_features,
        )
        return return_state

    def _initialize_triad(
        self,
        starting_time: Union[None, float] = None,
        winskip: Union[None, float] = None,
        winlen: Union[None, float] = None,
    ):
        min_time, max_time = (
            self.sampler.init_time,
            self.sampler.fin_time,
        )

        self.logger.debug("Restarting the environment")
        assert min_time != max_time, "Cap Reader not initialized Properly"

        # Starting Time
        if starting_time == None:
            self.starting_time = random.uniform(
                min_time,
                min_time + (max_time - min_time) * self.DAY_RIGHT_MARGIN,
            )
        else:
            assert within(
                starting_time, min_time, max_time * self.DAY_RIGHT_MARGIN
            ), f"Stating time {starting_time} out of range [{min_time},{max_time}]"
            self.starting_time = starting_time

        # Winskip
        if winskip == None:
            self.cur_winskip = random.uniform(
                self.WINDOW_SKIP_RANGE[0], self.WINDOW_SKIP_RANGE[1]
            )
        else:
            assert within(
                winskip, self.WINDOW_SKIP_RANGE[0], self.WINDOW_SKIP_RANGE[1]
            ), f"Winskip {winskip} out of range"
            self.cur_winskip = winskip

        if winlen == None:
            self.cur_winlen = random.uniform(
                self.WINDOW_LENGTH_RANGE[0], self.WINDOW_LENGTH_RANGE[1]
            )
        else:
            assert within(
                winlen, self.WINDOW_LENGTH_RANGE[0], self.WINDOW_LENGTH_RANGE[1]
            ), f"Winlen {winlen} out of range"
            self.cur_winlen = winlen