import pdb
from typing import Any, Sequence

import matplotlib.pyplot as plt
import numpy as np

from networking.common_lingo import ATTACK_TO_STRING, STRING_TO_ATTACKS, Attack
from sampleddetection.readers import AbstractTimeSeriesReader
from sampleddetection.samplers import DynamicWindowSampler, SampleFactory, binary_search


class WeightedSampler(DynamicWindowSampler):
    """
    Assumes that we are dealing with unequally distributes labels
    Expects its timeseries_rdr to contain weights for different time windows
    """

    def __init__(
        self,
        timeseries_rdr: AbstractTimeSeriesReader,
        # TOREM: Not really being used
        sampling_budget: int,
        num_bins: int,
        lowest_resolution: float = 1e-6,
    ):
        self.sampling_regions = []
        self.sr_weights = []
        self.timeseries_rdr = timeseries_rdr
        self._generate_regions(num_bins)
        super().__init__(
            timeseries_rdr,
            sampling_budget,
            lowest_resolution,
        )

    def _generate_regions(self, num_bins: int):
        # Calculate all divisions
        fin_time = self.timeseries_rdr.fin_time
        init_time = self.timeseries_rdr.init_time
        bins = np.linspace(init_time, fin_time, num_bins)
        lidx = 0
        num_samples_g = 1000

        labels_map = {
            Attack.BENIGN: Attack.BENIGN.value,
            Attack.HULK: Attack.HULK.value,
            Attack.GOLDENEYE: Attack.GOLDENEYE.value,
            Attack.SLOWLORIS: Attack.SLOWLORIS.value,
            Attack.SLOWHTTPTEST: Attack.SLOWHTTPTEST.value,
        }

        bins_times = []
        bins_labels = []
        for i, b in enumerate(bins):
            if i == 0:
                continue
            # Find the timestamp
            ridx = binary_search(self.timeseries_rdr, b)
            bins_times.append(b)

            # Just grab the first num_samples packets here and uset them to decide
            num_samples = min(num_samples_g, ridx - lidx)
            packs = self.timeseries_rdr[lidx : lidx + num_samples]
            packs_lbls = np.array([p.label.value for p in packs], dtype=np.int8)
            label = Attack.BENIGN.value  # By default
            if sum(packs_lbls == Attack.BENIGN.value) != num_samples:
                label = packs_lbls[packs_lbls != Attack.BENIGN.value][0]
                print("|", end="")

            lidx = ridx
            bins_labels.append(label)

        # Distribute sampling weights
        bl_np = np.array(bins_labels, dtype=np.int8)
        uni_weight = 1 / len(labels_map)
        perunit_weigth = np.zeros_like(bl_np, dtype=np.float32)
        for l in labels_map.values():
            idxs = np.where(bl_np == l)[0]
            perunit_weigth[idxs] = uni_weight / len(idxs)
        pdb.set_trace()

        # And lets plot it as a histogram just for funsies
        # bt_np = np.array(bins_times)
        # bl_np = np.array(bins_labels, dtype=np.int8)
        # bl_idxs = [bl_np[np.where(bl_np == l)] for l in labels_map.values()]
        # bts = [bt_np[np.where(bl_np == l)] for l in labels_map.values()]
        #
        # fig = plt.figure(figsize=(8, 19))
        # plt.tight_layout()
        # for i, l in enumerate(labels_map.keys()):
        #     print(f"Size of bts[{l}] is {len(bts[i])}")
        #     plt.scatter(bts[i], np.full_like(bts[i], 1), label=ATTACK_TO_STRING[l])
        # plt.legend()
        # plt.show()
        return bins_times, bins_labels, perunit_weigth

    def sample(
        self,
        starting_time: float,
        window_skip: float,
        window_length: float,
        initial_precise: bool = False,
        **kwargs,
    ) -> Sequence[Any]:
        # We first make sure that this is the first sample
        assert "fist_sample" in kwargs
        # We will first chose from one of

        return super().sample(
            starting_time, window_skip, window_length, initial_precise
        )

    def sample_debug(
        self,
        starting_time: float,
        window_skip: float,
        window_length: float,
        initial_precise: bool = False,
        first_sample: bool = False,
    ) -> Sequence[Any]:
        # We first make sure that this is the first sample
        # Chose from one of the bins
        norm_probs = self.perbin_weight[1:] / self.perbin_weight[1:].sum()
        choice_idx = int(
            np.random.choice(range(len(self.bins_times) - 1), 1, p=norm_probs).item()
        )
        attackid_to_label = {a.value: a for a in self.labels}
        # print(
        #     f"We chosen bin {choice_idx} corresponding to time {self.bins_times[choice_idx]}({to_canadian(self.bins_times[choice_idx])}) and label {attackid_to_label[self.bins_labels[choice_idx]]}"
        # )
        ltime = self.bins_times[choice_idx]
        rtime = self.bins_times[choice_idx + 1]

        # If we are on our first sample we are expected to chose it ourselves
        adj_starting_time = starting_time
        if first_sample == True:
            adj_starting_time = np.random.uniform(ltime, rtime, 1).item()

        actual_sample, debug_sample = super().sample_debug(
            adj_starting_time, window_skip, window_length, initial_precise
        )
        print(f"Chose time {adj_starting_time} from {ltime} to {rtime}")
        print(
            f"With amount of samples {len(actual_sample)} and debug sample {len(debug_sample)}"
        )
        return actual_sample, debug_sample
