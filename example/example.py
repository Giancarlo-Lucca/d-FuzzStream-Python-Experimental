import os
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import silhouette_samples, silhouette_score,adjusted_rand_score
from d_fuzzstream import DFuzzStreamSummarizer
from functions.merge import FuzzyDissimilarityMerger
from functions.distance import EuclideanDistance
from functions.membership import FuzzyCMeansMembership
from functions import metrics


def cluster_data(data, centers, fmics):
    distance = lambda a,b: np.sqrt(np.sum(np.power(a-b,2)))

    fmic_centroid = []
    for fmic in fmics:
        d_min = distance(fmic, centers[0])
        idx_min = 0
        for cidx, center in enumerate(centers):
            d = distance(fmic, center)
            if d < d_min:
                d_min = d
                idx_min = cidx
        fmic_centroid.append(idx_min)

    data_centroid = []
    for datai in data[data.columns[:-1]].values:
        d_min = distance(datai, fmics[0])
        idx_min = 0
        for fidx, fmic in enumerate(fmics):
            d = distance(datai, fmic)
            if d < d_min:
                d_min = d
                idx_min = fidx
        data_centroid.append(idx_min)

    data_final_centroid = [fmic_centroid[dc] for dc in data_centroid]

    data = np.column_stack([data, np.array(data_final_centroid)])

    return data


sm = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
      19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]
sm = [2]  # [32, 33]
min_fmics = 5
max_fmics = 100
thresh = 0.5
threshList = [0.25, 0.5, 0.65, 0.8, 0.9]
color = {'1': 'Red', '2': 'Blue', '3': 'Green', '4': 'Pink', 'nan': 'Gray'}
figure = plt.figure()
scatter = plt.scatter('x', 'y', s='radius', data={'x': [], 'y': [], 'radius': []})

datasetName = 'RBF1_40000'  # 'Benchmark1_11000'  # , 'RBF1_40000', 'Gaussian_4C2D800'

if (datasetName == 'Benchmark1_11000'):
    datasetPath = "https://raw.githubusercontent.com/CIG-UFSCar/DS_Datasets/master/Synthetic/Non-Stationary/Bench1_11k/Benchmark1_11000.csv"
    numChunks = 11  # it was 6x2000 but in the last one the offline wasn't called
    chunksize = 1000
    n_macro_clusters = 2
elif (datasetName == 'RBF1_40000'):
    datasetPath = "https://raw.githubusercontent.com/CIG-UFSCar/DS_Datasets/master/Synthetic/Non-Stationary/RBF1_40k/RBF1_40000.csv"
    numChunks = 40
    chunksize = 1000
    n_macro_clusters = 3
elif (datasetName == 'Gaussian_4C2D800'):
    datasetPath = "https://gitlab.citius.usc.es/david.gonzalez.marquez/GaussianMotionData/-/raw/master/SamplesFile_b_4C2D800Linear.csv?ref_type=heads"
    numChunks = 8
    chunksize = 100
    n_macro_clusters = 4
output_path = "".join(("./output/", datasetName, "/"))

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
Path(output_path).mkdir(exist_ok=True)

df = pd.DataFrame(columns=['SimMeasure', 'Threshold', 'StartChunk',
                           'EndChunk', 'Creations', 'Absorptions', 'Removals',
                           'Merges', 'Purity', 'pCoefficient', 'pEntropy',
                           'XieBeni', 'MPC', 'FukuyamaSugeno_1',
                           'FukuyamaSugeno_2', 'Silhouette'])  # 'ARI','Silhouette'])
for simIDX in sm:
    for thNum, threshIDX in enumerate(threshList):
        summarizer = DFuzzStreamSummarizer(
            distance_function=EuclideanDistance.distance,
            merge_threshold=threshIDX,
            merge_function=FuzzyDissimilarityMerger(simIDX, max_fmics).merge,
            membership_function=FuzzyCMeansMembership.memberships,
            chunksize=chunksize,
            n_macro_clusters=n_macro_clusters,
            time_gap=chunksize
        )

        summary = {'x': [], 'y': [], 'radius': [], 'color': [], 'weight': [], 'class': []}
        timestamp = 0

        # Read files in chunks
        with pd.read_csv(datasetPath,
                         # names=['X1','X2','class'],  # For Gaussian dataset only
                         dtype={"X1": float, "X2": float, "class": str},
                         chunksize=chunksize) as reader:
            for chunk in reader:
                print(f"Summarizing examples from {timestamp} to {timestamp + chunksize - 1} -> sim {simIDX} and thrsh {threshIDX}")
                for index, example in chunk.iterrows():
                    # Summarizing example
                    summarizer.summarize(example[0:2], example[2], timestamp)
                    timestamp += 1

                #  Compute ARI and Silhouette index. I suposse that the offline
                # step is done, because the chunk processing is finished
                fmicsc = [f.center.to_list() for f in summarizer.summary()]
                clusters = np.argmax(summarizer._Vmm, axis=0)
                point_fmic = []
                for _, point in chunk.iterrows():
                    d_min = EuclideanDistance.distance(point[:2], fmicsc[0])
                    id_min = 0
                    for i, fm in enumerate(fmicsc):
                        d = EuclideanDistance.distance(point[:2], fm)
                        if d < d_min:
                            d_min = d
                            id_min = i
                    point_fmic.append(clusters[id_min])
                y = chunk['class'].values
                y_h = np.array(point_fmic)
                not_nans = np.where(y.astype(str) != 'nan')[0].astype(int)
                ari = adjusted_rand_score(y[not_nans], y_h[not_nans])
                sil = silhouette_score(chunk[["X1", "X2"]].values, y_h)

                print(f"Offline ARI without outliers for {timestamp}: {ari}")
                print(f"Offline silhouette for {timestamp}: {sil}")
                print(f">> {timestamp},{sil:.5f},{ari:.5f}")

                # TODO: Obtain al metrics and create the row
                all_metrics = metrics.all_online_metrics(summarizer.summary(), chunksize)
                metrics_summary = ""
                for name, value in all_metrics.items():
                    metrics_summary += f"{name}: {round(value,3)}\n"
                metrics_summary = metrics_summary[:-1]

                row_metrics = list(all_metrics.values())
                row_timestamp = [simIDX, threshIDX, timestamp - chunksize, timestamp - 1]
                row_m = [summarizer.metrics['creations'], summarizer.metrics['absorptions'], summarizer.metrics['removals'], summarizer.metrics['merges']]

                # Silhouete
                fmics = [fmic.center.to_list() for fmic in summarizer.summary()]
                data = cluster_data(chunk, summarizer._V, fmics)
                # ari = adjusted_rand_score(data[:,-2],data[:,-1])
                sil = silhouette_score(data[:, :-2], data[:, -1])
                # print(timestamp, f"{ari=}, {sil=}")

                row_s = [sil]  # row_s = [ari, sil]

                new_row = pd.DataFrame([row_timestamp + row_m + row_metrics + row_s],
                                       columns=df.columns)
                df = pd.concat([df, new_row], ignore_index=True)

                # print("Total de Fmics = "+str(len(summarizer.summary())))
                for fmic in summarizer.summary():
                    # for k, v in fmic.sumPointsPerClassd.items():  # FIXME: Not sorted, but sorted() has problems with nan
                        # print(f"Total pontos classe {k} = {v}")

                    summary['x'].append(fmic.center[0])
                    summary['y'].append(fmic.center[1])
                    summary['radius'].append(fmic.radius * 100000)
                    summary['color'].append(color[max(fmic.tags, key=fmic.tags.get)])
                    summary['weight'].append(fmic.m)

                if not os.path.isdir("./Img/"):
                    os.mkdir("./Img/")

                # fig = plt.figure()
                # # Plot radius
                # plt.scatter('x', 'y', s='radius', color='color', data=summary, alpha=0.1)
                # # Plot centroids
                # plt.scatter('x', 'y', s=1, color='color', data=summary)
                # # plt.legend(["color blue", "color green"], loc ="lower right")
                # # plt.legend(["Purity"+str(summarizer.Purity()),"PartitionCoefficient"+str(summarizer.PartitionCoefficient()),"PartitionEntropy"+str(summarizer.PartitionEntropy()),"XieBeni"+str(summarizer.XieBeni()), "FukuyamaSugeno_1"+str(summarizer.FukuyamaSugeno_1()),"FukuyamaSugeno_2"+str(summarizer.FukuyamaSugeno_2())], bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0)
                # plt.figtext(.8, .8, "T = 4K")
                # side_text = plt.figtext(.91, .8, metrics_summary)
                # fig.subplots_adjust(top=1.0)
                # # plt.show()
                # fig.savefig("./Img/[Chunk "+str(timestamp - chunksize)+" to "+str(timestamp - 1)+"] Sim("+str(simIDX)+")_Thresh("+str(threshIDX)+").png", bbox_extra_artists=(side_text,), bbox_inches='tight')
                # plt.close()


            # Transforming FMiCs into dataframe
            for fmic in summarizer.summary():
                summary['x'].append(fmic.center[0])
                summary['y'].append(fmic.center[1])
                summary['radius'].append(fmic.radius * 100000)
                summary['color'].append(color[max(fmic.tags, key=fmic.tags.get)])
                summary['weight'].append(fmic.m)
                summary['class'].append(max(fmic.tags, key=fmic.tags.get))

            print("==== Approach ====")
            print("Similarity = ", simIDX)
            print("Threshold = ", threshIDX)
            # print("==== Summary ====")
            # print(summary)
            print("==== Metrics ====")
            print(summarizer.metrics)
            # print("\n")
            # print(df)
            print("------")


        df.to_excel("".join((output_path, "summary_and_metrics_" + datasetName + "2.xlsx")))
print("--- End of execution --- ")
