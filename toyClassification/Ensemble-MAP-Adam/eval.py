# code-checked
# server-checked

from model import ToyNet

import torch
import torch.utils.data
import torch.nn as nn
from torch.autograd import Variable
import torch.optim as optim
import torch.nn.functional as F

import numpy as np
import pickle
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import cv2

batch_size = 32

M = 1

x_min = -6.0
x_max = 6.0
num_points = 60

networks = []
for i in range(M):
    network = ToyNet("eval_Ensemble-MAP-Adam_1_M1024", project_dir="./root/evaluating_bdl/toyClassification").cuda()
    network.load_state_dict(torch.load("./root/evaluating_bdl/toyClassification/training_logs/model_Ensemble-MAP-Adam_1_M1024_%d/checkpoints/model_Ensemble-MAP-Adam_1_M1024_epoch_150.pth" % i))
    networks.append(network)

M = float(len(networks))
print (M)

for network in networks:
    network.eval()

false_prob_values = np.zeros((num_points, num_points))
x_values = np.linspace(x_min, x_max, num_points, dtype=np.float32)
for x_1_i, x_1_value in enumerate(x_values):
    for x_2_i, x_2_value in enumerate(x_values):
        x = torch.from_numpy(np.array([x_1_value, x_2_value])).unsqueeze(0).cuda() # (shape: (1, 2))

        mean_prob_vector = np.zeros((2, ))
        for network in networks:
            logits = network(x) # (shape: (1, num_classes)) (num_classes==2)
            prob_vector = F.softmax(logits, dim=1) # (shape: (1, num_classes))

            prob_vector = prob_vector.data.cpu().numpy()[0] # (shape: (2, ))

            mean_prob_vector += prob_vector/M

        false_prob_values[x_2_i, x_1_i] = mean_prob_vector[0]

plt.figure(1)
x_1, x_2 = np.meshgrid(x_values, x_values)
plt.pcolormesh(x_1, x_2, false_prob_values, cmap="RdBu")
plt.xlabel("x_1")
plt.ylabel("x_2")
plt.title("Predictive Density")
plt.colorbar()
plt.savefig("%s/predictive_density.png" % network.model_dir)
plt.close(1)
plt.figure(1)
plt.pcolormesh(x_1, x_2, false_prob_values, cmap="binary")
plt.xlabel("x_1")
plt.ylabel("x_2")
plt.title("Predictive Density")
plt.colorbar()
plt.savefig("%s/predictive_density_gray.png" % network.model_dir)
plt.close(1)

x_values = np.linspace(x_min, x_max, 1000, dtype=np.float32)
x_1, x_2 = np.meshgrid(x_values, x_values)
dist = np.sqrt(x_1**2 + x_2**2)
false_prob_values_GT = np.zeros(dist.shape)
false_prob_values_GT[dist < 2.4] = 1.0
plt.figure(1)
plt.pcolormesh(x_1, x_2, false_prob_values_GT, cmap="RdBu")
plt.xlabel("x_1")
plt.ylabel("x_2")
plt.title("Predictive Density - Ground Truth")
plt.colorbar()
plt.savefig("%s/predictive_density_GT.png" % network.model_dir)
plt.close(1)
plt.figure(1)
plt.pcolormesh(x_1, x_2, false_prob_values_GT, cmap="binary")
plt.xlabel("x_1")
plt.ylabel("x_2")
plt.title("Predictive Density - Ground Truth")
plt.colorbar()
plt.savefig("%s/predictive_density_gray_GT.png" % network.model_dir)
plt.close(1)

with open("./root/evaluating_bdl/toyClassification/HMC/false_prob_values.pkl", "rb") as file: # (needed for python3)
    false_prob_values_HMC = pickle.load(file) # (shape: (60, 60))
x_values = np.linspace(x_min, x_max, num_points, dtype=np.float32)
x_1, x_2 = np.meshgrid(x_values, x_values)
x_values_GT = np.linspace(x_min, x_max, 1000, dtype=np.float32)
x_1_GT, x_2_GT = np.meshgrid(x_values_GT, x_values_GT)
fig, axes = plt.subplots(nrows=1, ncols=2, constrained_layout=True, sharex=True, sharey=True, figsize=(11.0, 5.0))
im = axes.flat[0].pcolormesh(x_1, x_2, false_prob_values_HMC, cmap="RdBu", vmin=0, vmax=1)
im = axes.flat[1].pcolormesh(x_1, x_2, false_prob_values, cmap="RdBu", vmin=0, vmax=1)
fig.colorbar(im, ax=axes.flat)
plt.savefig("%s/predictive_density_comparison.png" % network.model_dir)
plt.close()

M = int(M)

fc1_weight_samples = np.zeros((M, 1, 10, 2))
fc1_bias_samples = np.zeros((M, 1, 10))
fc2_weight_samples = np.zeros((M, 1, 10, 10))
fc2_bias_samples = np.zeros((M, 1, 10))
fc3_weight_samples = np.zeros((M, 1, 2, 10))
fc3_bias_samples = np.zeros((M, 1, 2))
for index, network in enumerate(networks):
    for name, param in network.named_parameters():
        if name == "fc1.weight":
            fc1_weight_samples[index, 0, :] = param.data.cpu().numpy()
        elif name == "fc1.bias":
            fc1_bias_samples[index, 0, :] = param.data.cpu().numpy()
        elif name == "fc2.weight":
            fc2_weight_samples[index, 0, :] = param.data.cpu().numpy()
        elif name == "fc2.bias":
            fc2_bias_samples[index, 0, :] = param.data.cpu().numpy()
        elif name == "fc3.weight":
            fc3_weight_samples[index, 0, :] = param.data.cpu().numpy()
        elif name == "fc3.bias":
            fc3_bias_samples[index, 0, :] = param.data.cpu().numpy()
        else:
            raise Exception("Unknown network parameter!")

import os
if not os.path.exists("%s/param_distributions" % (network.model_dir)):
    os.makedirs("%s/param_distributions" % (network.model_dir))

# (fc1_weight_samples has shape: (M, 1, 10, 2))
for param_index_i in range(10):
    for param_index_j in range(2):
        values = fc1_weight_samples[:, 0, param_index_i, param_index_j] # (shape: (M, ))
        plt.figure(1)
        plt.hist(np.array(values), bins=100)
        plt.savefig("%s/param_distributions/fc1_weight_%d_%d.png" % (network.model_dir, param_index_i, param_index_j))
        plt.close(1)

# (fc1_bias_samples has shape: (M, 1, 10))
for param_index in range(10):
    values = fc1_bias_samples[:, 0, param_index] # (shape: (M, ))
    plt.figure(1)
    plt.hist(np.array(values), bins=100)
    plt.savefig("%s/param_distributions/fc1_bias_%d.png" % (network.model_dir, param_index))
    plt.close(1)

# (fc2_weight_samples has shape: (M, 1, 10, 10))
for param_index_i in range(10):
    for param_index_j in range(10):
        values = fc2_weight_samples[:, 0, param_index_i, param_index_j] # (shape: (M, ))
        plt.figure(1)
        plt.hist(np.array(values), bins=100)
        plt.savefig("%s/param_distributions/fc2_weight_%d_%d.png" % (network.model_dir, param_index_i, param_index_j))
        plt.close(1)

# (fc2_bias_samples has shape: (M, 1, 10))
for param_index in range(10):
    values = fc2_bias_samples[:, 0, param_index] # (shape: (M, ))
    plt.figure(1)
    plt.hist(np.array(values), bins=100)
    plt.savefig("%s/param_distributions/fc2_bias_%d.png" % (network.model_dir, param_index))
    plt.close(1)

# (fc3_weight_samples has shape: (M, 1, 2, 10))
for param_index_i in range(2):
    for param_index_j in range(10):
        values = fc3_weight_samples[:, 0, param_index_i, param_index_j] # (shape: (M, ))
        plt.figure(1)
        plt.hist(np.array(values), bins=100)
        plt.savefig("%s/param_distributions/fc3_weight_%d_%d.png" % (network.model_dir, param_index_i, param_index_j))
        plt.close(1)

# (fc3_bias_samples has shape: (M, 1, 2))
for param_index in range(2):
    values = fc3_bias_samples[:, 0, param_index] # (shape: (M, ))
    plt.figure(1)
    plt.hist(np.array(values), bins=100)
    plt.savefig("%s/param_distributions/fc3_bias_%d.png" % (network.model_dir, param_index))
    plt.close(1)
