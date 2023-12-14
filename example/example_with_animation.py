import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from d_fuzzstream import DFuzzStreamSummarizer
from functions.merge import FuzzyDissimilarityMerger
from functions.distance import EuclideanDistance
from functions.membership import FuzzyCMeansMembership

idxSimilarity = 5
min_fmics = 5
max_fmics = 100
thresh = 1.2



summarizer = DFuzzStreamSummarizer(
    distance_function=EuclideanDistance.distance,
    merge_threshold = thresh,
    merge_function=FuzzyDissimilarityMerger(idxSimilarity, max_fmics).merge,
    membership_function=FuzzyCMeansMembership.memberships,
)

chunk_size = 1000
figure = plt.figure()
scatter = plt.scatter('x', 'y', s='radius', data={'x': [], 'y': [], 'radius': []})

# Read files in chunks
csv = pd.read_csv("https://raw.githubusercontent.com/CIG-UFSCar/DS_Datasets/master/Synthetic/Non-Stationary/Bench1_11k/Benchmark1_11000.csv",
                  dtype={"X1": float, "X2": float, "class": str},
                  chunksize=chunk_size)

color = {'1': 'Red', '2': 'Blue', 'nan': 'Gray'}


# Function to animate GIF
def summarize(frame):
    plt.cla()
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    chunk = next(csv)

    timestamp = chunk_size * frame

    print(f"Summarizing examples from {timestamp} to {timestamp + chunk_size - 1}")
    for index, example in chunk.iterrows():
        # Summarizing example
        summarizer.summarize(example[0:2], example[2], timestamp)
        timestamp += 1

    data = {'x': [], 'y': [], 'radius': [], 'color': []}

    for fmic in summarizer.summary():
        data['x'].append(fmic.center[0])
        data['y'].append(fmic.center[1])
        data['radius'].append(fmic.radius * 100000)
        data['color'].append(color[max(fmic.tags, key=fmic.tags.get)])
    # Plot radius
    plt.scatter('x', 'y', s='radius', color='color', data=data, alpha=0.1)
    # Plot centroids
    plt.scatter('x', 'y', s=1, color='color', data=data)


anim = FuncAnimation(
    figure,
    summarize,
    frames=11000//chunk_size,
    interval=1000,
    repeat=False,
    init_func=lambda: None
)

writer_gif = PillowWriter(fps=1)

anim.save("summary_sm_"+str(idxSimilarity)+"th_"+str(thresh)+".gif", writer=writer_gif)

plt.close()
csv.close()

print("==== Metrics ====")
print(summarizer.metrics)
