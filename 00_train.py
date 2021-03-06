########################################################################
# import default libraries
########################################################################
import os
import sys
import gc
########################################################################


########################################################################
# import additional libraries
########################################################################
import numpy as np
import scipy.stats
# from import
from numpy import vstack, hstack
from tqdm import tqdm

try:
    from sklearn.externals import joblib
except:
    import joblib
# original lib
import common as com
import keras_model

########################################################################


########################################################################
# load parameter.yaml
########################################################################
param = com.yaml_load()


########################################################################


########################################################################
# visualizer
########################################################################
class visualizer(object):
    def __init__(self):
        import matplotlib.pyplot as plt
        import librosa as lib
        import pylab as py
        self.py = py
        self.lib = lib
        self.plt = plt
        self.fig = self.plt.figure(figsize=(7, 5))
        self.plt.subplots_adjust(wspace=0.3, hspace=0.3)

    def loss_plot(self, loss, val_loss):
        """
        Plot loss curve.

        loss : list [ float ]
            training loss time series.
        val_loss : list [ float ]
            validation loss time series.

        return   : None
        """
        ax = self.fig.add_subplot(1, 1, 1)
        ax.cla()
        ax.plot(loss)
        ax.plot(val_loss)
        ax.set_title("Model loss")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.legend(["Train", "Validation"], loc="upper right")

    # def plot_spectrogram(self, log_mel_spectrogran):
    #   self.py.axis('off')  # no axis
    #  self.py.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[])
    # self.lib.display.specshow(self.lib.power_to_db(log_mel_spectrogran, ref=np.max))
    def save_figure(self, name):
        """
        Save figure.

        name : str
            save png file path.

        return : None
        """
        self.plt.savefig(name)


########################################################################


########################################################################
# get data from the list for file paths
########################################################################
def file_list_to_data(file_list,
                      msg="calc...",
                      n_mels=64,
                      n_frames=5,
                      n_hop_frames=1,
                      n_fft=1024,
                      hop_length=512,
                      power=2.0):
    """
    convert the file_list to a vector array.
    file_to_vector_array() is iterated, and the output vector array is concatenated.

    file_list : list [ str ]
        .wav filename list of dataset
    msg : str ( default = "calc..." )
        description for tqdm.
        this parameter will be input into "desc" param at tqdm.

    return : numpy.array( numpy.array( float ) )
        data for training (this function is not used for test.)
        * dataset.shape = (number of feature vectors, dimensions of feature vectors)
    """
    # calculate the number of dimensions
    dims = n_mels * n_frames

    # iterate file_to_vector_array()
    for idx in tqdm(range(len(file_list)), desc=msg):
        vectors = com.file_to_vectors(file_list[idx],
                                      n_mels=n_mels,
                                      n_frames=n_frames,
                                      n_fft=n_fft,
                                      hop_length=hop_length,
                                      power=power)
        # vectors2 = com.file_to_vectors2(file_list[idx],
        #                               n_mels=n_mels,
        #                              n_frames=n_frames,
        #                             n_fft=n_fft,
        #                            hop_length=hop_length,
        #                           power=power)
        vectors = vectors[:: n_hop_frames, :]
        # augemented_vectors = augemented_vectors[:: n_hop_frames, ::]
        # vectors2 = vectors2[:: n_hop_frames, :]

        if idx == 0:
            data = np.zeros((len(file_list) * vectors.shape[0], dims), float)
            # data_augmented = np.zeros((len(file_list) * augemented_vectors.shape[0], dims), float)

        data[vectors.shape[0] * idx: vectors.shape[0] * (idx + 1), :] = vectors
        # print(len(data))
        # data_augmented[augemented_vectors.shape[0] * idx: augemented_vectors.shape[0] * (idx + 1),
        #:] = augemented_vectors
        # output = np.concatenate((data_augmented, data), axis=0)
    return data
    # return output


########################################################################

def file_list_to_data2(file_list,
                       msg="calc...",
                       n_mels=64,
                       n_frames=5,
                       n_hop_frames=1,
                       n_fft=1024,
                       hop_length=512,
                       power=2.0):
    print("hey")
    dims = n_mels * n_frames
    for idx in tqdm(range(len(file_list)), desc=msg):
        vectors2 = com.file_to_vectors2(file_list[idx],
                                        n_mels=n_mels,
                                        n_frames=n_frames,
                                        n_fft=n_fft,
                                        hop_length=hop_length,
                                        power=power)

        vectors2 = vectors2[:: n_hop_frames, :]
        if idx == 0:
            data2 = np.zeros((len(file_list) * vectors2.shape[0], dims), float)
        data2[vectors2.shape[0] * idx: vectors2.shape[0] * (idx + 1), :] = vectors2
    return data2


########################################################################
# main 00_train.py
########################################################################
if __name__ == "__main__":
    # check mode
    # "development": mode == True
    # "evaluation": mode == False
    mode = com.command_line_chk()
    if mode is None:
        sys.exit(-1)

    # make output directory
    os.makedirs(param["model_directory"], exist_ok=True)

    # initialize the visualizer
    visualizer = visualizer()

    # load base_directory list
    dirs = com.select_dirs(param=param, mode=mode)

    # loop of the base directory
    for idx, target_dir in enumerate(dirs):
        print("\n===========================")
        print("[{idx}/{total}] {target_dir}".format(target_dir=target_dir, idx=idx + 1, total=len(dirs)))

        # set path
        machine_type = os.path.split(target_dir)[1]
        model_file_path = "{model}/model_{machine_type}.hdf5".format(model=param["model_directory"],
                                                                     machine_type=machine_type)

        if os.path.exists(model_file_path):
            com.logger.info("model exists")
            continue

        history_img = "{model}/history_{machine_type}.png".format(model=param["model_directory"],
                                                                  machine_type=machine_type)
        # updated_img = "{model}/history_{machine_type}.jpg".format(model=param["model_directory"],
        #                                                         machine_type=machine_type)
        # pickle file for storing anomaly score distribution
        score_distr_file_path = "{model}/score_distr_{machine_type}.pkl".format(model=param["model_directory"],
                                                                                machine_type=machine_type)

        # generate dataset
        print("============== DATASET_GENERATOR ==============")

        # get file list for all sections
        # all values of y_true are zero in training
        files, y_true = com.file_list_generator(target_dir=target_dir,
                                                section_name="*",
                                                dir_name="train",
                                                mode=mode)

        data = file_list_to_data(files,
                                 msg="generate train_dataset",
                                 n_mels=param["feature"]["n_mels"],
                                 n_frames=param["feature"]["n_frames"],
                                 n_hop_frames=param["feature"]["n_hop_frames"],
                                 n_fft=param["feature"]["n_fft"],
                                 hop_length=param["feature"]["hop_length"],
                                 power=param["feature"]["power"])
        # dataNew = file_list_to_data2(files,
        #                            msg="generate train_dataset",
        #                           n_mels=param["feature"]["n_mels"],
        #                          n_frames=param["feature"]["n_frames"],
        #                         n_hop_frames=param["feature"]["n_hop_frames"],
        #                        n_fft=param["feature"]["n_fft"],
        #                       hop_length=param["feature"]["hop_length"],
        #                      power=param["feature"]["power"])

        # X_both, y_both = vstack((data, dataNew)), hstack((data, dataNew))

        # number of vectors for each wave file
        n_vectors_ea_file = int(data.shape[0] / len(files))

        # train model
        print("============== MODEL TRAINING ==============")
        model = keras_model.get_model(param["feature"]["n_mels"] * param["feature"]["n_frames"],
                                      param["fit"]["lr"])

        model.summary()

        history = model.fit(x=data,
                            y=data,
                            epochs=param["fit"]["epochs"],
                            batch_size=param["fit"]["batch_size"],
                            shuffle=param["fit"]["shuffle"],
                            validation_split=param["fit"]["validation_split"],
                            verbose=param["fit"]["verbose"])

        # calculate y_pred for fitting anomaly score distribution
        y_pred = []
        start_idx = 0
        for file_idx in range(len(files)):
            y_pred.append(np.mean(np.square(data[start_idx: start_idx + n_vectors_ea_file, :]
                                            - model.predict(data[start_idx: start_idx + n_vectors_ea_file, :]))))
            start_idx += n_vectors_ea_file

        # fit anomaly score distribution
        shape_hat, loc_hat, scale_hat = scipy.stats.gamma.fit(y_pred)
        gamma_params = [shape_hat, loc_hat, scale_hat]
        joblib.dump(gamma_params, score_distr_file_path)

        visualizer.loss_plot(history.history["loss"], history.history["val_loss"])
        visualizer.save_figure(history_img)
        # visualizer.plot_spectrogram(data)
        # visualizer.save_figure(updated_img)
        model.save(model_file_path)
        com.logger.info("save_model -> {}".format(model_file_path))
        print("============== END TRAINING ==============")

        del data
        del model
        keras_model.clear_session()
        gc.collect()
