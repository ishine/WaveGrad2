import argparse

import torch
import yaml
import torch.nn as nn
from torch.utils.data import DataLoader

from utils.model import get_model
from utils.tools import to_device, log, synth_one_sample
from model import WaveGrad2Loss
from dataset import Dataset


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def evaluate(model, step, configs, STFT, logger=None, loss_len=6):
    preprocess_config, model_config, train_config = configs

    # Get dataset
    dataset = Dataset(
        "val.txt", preprocess_config, train_config, sort=True, drop_last=False
    )
    batch_size = train_config["optimizer"]["batch_size"]
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=dataset.collate_fn,
    )

    # Get loss function
    Loss = WaveGrad2Loss(preprocess_config, model_config).to(device)

    # Evaluation
    loss_sums = [0 for _ in range(loss_len)]
    for batchs in loader:
        for batch in batchs:
            batch = to_device(batch, device)

            with torch.no_grad():
                # Forward
                output = model(*(batch[2:]))

                # Cal Loss
                losses = Loss(batch, output)

                for i in range(len(losses)):
                    loss_sums[i] += losses[i].item() * len(batch[0])

    loss_means = [loss_sum / len(dataset) for loss_sum in loss_sums]

    message = "Validation Step {}, Total Loss: {:.4f}, Noise Loss: {:.4f}, Duration Loss: {:.4f}".format(
        *([step] + [l for l in loss_means])
    )

    if logger is not None:
        fig, wav_reconstruction, wav_prediction, tag = synth_one_sample(
            model,
            batch,
            output,
            STFT,
        )

        log(logger, step, losses=loss_means)
        log(
            logger,
            fig=fig,
            tag="Validation/step_{}_{}".format(step, tag),
        )
        sampling_rate = preprocess_config["preprocessing"]["audio"]["sampling_rate"]
        log(
            logger,
            audio=wav_reconstruction,
            sampling_rate=sampling_rate,
            tag="Validation/step_{}_{}_reconstructed".format(step, tag),
        )
        log(
            logger,
            audio=wav_prediction,
            sampling_rate=sampling_rate,
            tag="Validation/step_{}_{}_synthesized".format(step, tag),
        )

    return message
