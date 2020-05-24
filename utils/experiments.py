import GP_models.GP_sig_precomputed as GP_sig
import GP_models.GP_sig_ARD as GP_sig_ARD
import GP_models.GP_sig_ARD_full as GP_sig_ARD_full
import GP_models.GP_classic as GP_naive
import GP_models.GP_classic_arbitrary_items as GP_naive_arbitrary_items
from sklearn.model_selection import KFold
from sklearn.model_selection import StratifiedKFold
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import numpy as np
from matplotlib import pyplot as plt
import seaborn as sns
from importlib import reload

reload(GP_naive_arbitrary_items)


def precompute_K(X):
    K_precomputed = np.zeros((len(X), len(X)))

    for i in range(len(X)):
        for j in range(i + 1):
            K_precomputed[i][j] = 1. + np.dot(X[i], X[j])
            K_precomputed[j][i] = K_precomputed[i][j]
    return K_precomputed


def augment_K_precomputed(K_precomputed, X_train, x_test):
    K_aug = np.zeros((len(X_train) + 1, len(X_train) + 1))
    K_aug[:len(X_train), :len(X_train)] = K_precomputed
    for i in range(len(X_train)):
        K_aug[-1, i] = 1. + np.dot(X_train[i], x_test)
        K_aug[i, -1] = K_aug[-1, i]
    K_aug[-1][-1] = 1. + np.dot(x_test, x_test)
    return K_aug


def loss_naive(x, y, train_index, test_index):
    y_train, y_test = y[train_index], y[test_index]
    x_train, x_test = x[train_index], x[test_index]

    x_train = torch.tensor(x_train, dtype=torch.float64).transpose(1, 2)
    x_test = torch.tensor(x_test, dtype=torch.float64).transpose(1, 2)

    model = GP_naive.GP(x_train, torch.tensor(y_train, dtype=torch.float64), 0, 0, 0,
                        ['lengthscale', 'variance', 'noise'])

    GP_naive.plot_marginal_log_lik(model)


def loss_sig(K_precomputed, y, train_index, test_index):
    model = GP_sig.GP(np.zeros(int(len(train_index))), None, 0, 0, 0, ['lengthscale', 'variance', 'noise'], 0)

    y_train, y_test = y[train_index], y[test_index]

    model.Y = torch.tensor(y_train, dtype=torch.float64)

    K = GP_sig.get_K(K_precomputed, train_index)
    K_s = GP_sig.get_K(K_precomputed, train_index, test_index)
    K_ss = GP_sig.get_K(K_precomputed, test_index)

    model.K = torch.tensor(K, dtype=torch.float64)

    GP_sig.plot_marginal_log_lik(model)


def naive_experiment_arbitrary(x, y, train_index, ARD=False, RBF_top=False, param_init=[0, 0, 0], plot=False,
                               device=torch.device("cuda")):
    if plot:
        sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 1.5})
        fig, axs = plt.subplots(1, 3, figsize=(35, 7))
        axs = axs.ravel()

    y_train, y_test = y[:train_index], y[train_index:]
    x_train, x_test = x[:train_index], x[train_index:]

    # x_train is of shape N_bags x N_items x time*D
    # changed into N_bags x timexD x N_items

    x_train = [torch.Tensor(e).transpose(0, 1) for e in x_train]
    x_test = [torch.Tensor(e).transpose(0, 1) for e in x_test]

    model = GP_naive_arbitrary_items.GP(x_train, torch.Tensor(y_train), param_init[0],
                                        param_init[1], param_init[2], param_init[3],
                                        ['lengthscale', 'variance', 'noise'], ARD=ARD, device=device)
    if plot:
        print('start training')
        GP_naive_arbitrary_items.train(model, 2000, RBF_top=RBF_top, plot=plot, ax=axs[0])
    else:
        GP_naive_arbitrary_items.train(model, 2000, RBF_top=RBF_top)

    # for arbitrary

    mu_test, stdv_test = model.predict(x_train, x_test, RBF_top=RBF_top, test=True)
    mu_train, stdv_train = model.predict(x_train, x_train, RBF_top=RBF_top, test=False)
    R2_train = compute_r2(y_train[:, 0], mu_train[:, 0])
    R2_test = compute_r2(y_test[:, 0], mu_test[:, 0])
    RMSE_train = compute_rmse(y_train[:, 0], mu_train[:, 0])
    RMSE_test = compute_rmse(y_test[:, 0], mu_test[:, 0])
    MAPE_train = compute_MAPE(y_train[:, 0], mu_train[:, 0])
    MAPE_test = compute_MAPE(y_test[:, 0], mu_test[:, 0])

    # fig, axs = plt.subplots(1, 1, figsize=(15, 7))
    # ax = plt.figure(figsize=(25, 7))

    # regression_models.plot_fit(axs[0], y_train[:, 0], mu_train[:, 0], std=stdv_train, sklearn=True)
    # regression_models.plot_fit(axs, y_test[:, 0], mu_test[:, 0], std=stdv_test, sklearn=True)
    if plot:
        plot_fit(axs[1], y_train[:, 0], mu_train[:, 0], std=stdv_train, sklearn=True)
        plot_fit(axs[2], y_test[:, 0], mu_test[:, 0], std=stdv_test, sklearn=True)
        plt.show()
    # fig = plt.figure(figsize=(25, 7))
    # regression_models.plot_extrapolation(y_train[:, 0], mu_train[:, 0], stdv_train, y_test[:, 0], mu_test[:, 0],
    #                                    stdv_test)
    # plt.show()

    return RMSE_train, R2_train, MAPE_train, RMSE_test, R2_test, MAPE_test


def naive_experiment(x, y, train_index, test_index, ARD=False, RBF_top=False, param_init=[0, 0, 0], plot=False,
                     device=torch.device("cuda")):
    if plot:
        sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 1.5})
        fig, axs = plt.subplots(1, 3, figsize=(35, 7))
        axs = axs.ravel()

    y_train, y_test = y[train_index], y[test_index]
    x_train, x_test = x[train_index], x[test_index]

    # for 1d data

    # x_train is of shape N_bags x N_items x time
    # changed into N_bags x time x N_items

    x_train = torch.tensor(x_train, dtype=torch.float64, device=device).transpose(1, 2)
    x_test = torch.tensor(x_test, dtype=torch.float64, device=device).transpose(1, 2)

    model = GP_naive.GP(x_train, torch.tensor(y_train, dtype=torch.float64), param_init[0], param_init[1],
                        param_init[2], param_init[3],
                        ['lengthscale', 'variance', 'noise'], ARD=ARD, device=device)
    if plot:
        GP_naive.train(model, 2000, RBF_top=RBF_top, plot=plot, ax=axs[0])
    else:
        GP_naive.train(model, 2000, RBF_top=RBF_top)

    mu_test, stdv_test = model.predict(x_train, x_test, RBF_top=RBF_top)
    mu_train, stdv_train = model.predict(x_train, RBF_top=RBF_top)
    R2_train = compute_r2(y_train[:, 0], mu_train[:, 0])
    R2_test = compute_r2(y_test[:, 0], mu_test[:, 0])
    RMSE_train = compute_rmse(y_train[:, 0], mu_train[:, 0])
    RMSE_test = compute_rmse(y_test[:, 0], mu_test[:, 0])
    MAPE_train = compute_MAPE(y_train[:, 0], mu_train[:, 0])
    MAPE_test = compute_MAPE(y_test[:, 0], mu_test[:, 0])

    # fig, axs = plt.subplots(1, 1, figsize=(15, 7))
    # ax = plt.figure(figsize=(25, 7))

    # regression_models.plot_fit(axs[0], y_train[:, 0], mu_train[:, 0], std=stdv_train, sklearn=True)
    # regression_models.plot_fit(axs, y_test[:, 0], mu_test[:, 0], std=stdv_test, sklearn=True)
    if plot:
        plot_fit(axs[1], y_train[:, 0], mu_train[:, 0], std=stdv_train, sklearn=True)
        plot_fit(axs[2], y_test[:, 0], mu_test[:, 0], std=stdv_test, sklearn=True)
        plt.show()
    # fig = plt.figure(figsize=(25, 7))
    # regression_models.plot_extrapolation(y_train[:, 0], mu_train[:, 0], stdv_train, y_test[:, 0], mu_test[:, 0],
    #                                    stdv_test)
    # plt.show()

    return RMSE_train, R2_train, MAPE_train, RMSE_test, R2_test, MAPE_test


def experiment_precomputed(K_precomputed, y, train_index, test_index, param_init=[0, 0, 0], RBF=False, plot=False,
                           device=torch.device("cpu"), ARD_full=False):
    if plot:
        sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 1.5})
        fig, axs = plt.subplots(1, 3, figsize=(35, 7))
        axs = axs.ravel()

    y_train, y_test = y[train_index], y[test_index]

    if RBF:
        model = GP_sig.GP(np.zeros(int(len(train_index))), torch.tensor(y_train, dtype=torch.float64, device=device),
                          param_init[0], param_init[1], param_init[2], ['lengthscale', 'variance', 'noise'], 0,
                          device=device)
    else:
        model = GP_sig.GP(np.zeros(int(len(train_index))), torch.tensor(y_train, dtype=torch.float64, device=device),
                          param_init[0], param_init[1], param_init[2], ['variance', 'noise'], 0, device=device)

    K = GP_sig.get_K(K_precomputed, train_index)
    K_s = GP_sig.get_K(K_precomputed, train_index, test_index)
    K_ss = GP_sig.get_K(K_precomputed, test_index)

    model.K = torch.tensor(K, dtype=torch.float64, device=device)
    if plot:
        GP_sig.train(model, 20000, RBF=RBF, plot=plot, ax=axs[0])
    else:
        GP_sig.train(model, 20000, RBF=RBF, plot=plot)

    if RBF:
        model.K_full = model.get_K_RBF_Sig(torch.tensor(K_precomputed, dtype=torch.float64, device=device))
        model.indices_1 = train_index
        model.indices_2 = test_index
        mu_test, stdv_test = model.dummy_predict(K_s, K_ss, RBF=RBF)
        model.indices_2 = train_index
        mu_train, stdv_train = model.dummy_predict(K, K, RBF=RBF)
    else:
        mu_test, stdv_test = model.dummy_predict(K_s, K_ss, RBF=RBF)
        mu_train, stdv_train = model.dummy_predict(K, K, RBF=RBF)

    R2_train = compute_r2(y_train[:, 0], mu_train[:, 0])
    RMSE_train = compute_rmse(y_train[:, 0], mu_train[:, 0])
    MAPE_train = compute_MAPE(y_train[:, 0], mu_train[:, 0])

    R2_test = compute_r2(y_test[:, 0], mu_test[:, 0])
    RMSE_test = compute_rmse(y_test[:, 0], mu_test[:, 0])
    MAPE_test = compute_MAPE(y_test[:, 0], mu_test[:, 0])

    # ax = plt.figure(figsize=(25, 7))
    # regression_models.plot_fit(axs[0], y_train[:, 0], mu_train[:, 0], std=stdv_train, sklearn=True)

    if plot:
        plot_fit(axs[1], y_train[:, 0], mu_train[:, 0], std=stdv_train, sklearn=True)
        plot_fit(axs[2], y_test[:, 0], mu_test[:, 0], std=stdv_test, sklearn=True)
        order = np.argsort(y_test[:, 0])
        plt.show()
    # fig = plt.figure(figsize=(25, 7))
    # regression_models.plot_extrapolation(y_train[:, 0], mu_train[:, 0], stdv_train,y_test[:, 0], mu_test[:, 0], stdv_test)
    # plt.show()
    predictions = {'mu_train': mu_train, 'stdv_train': stdv_train, 'mu_test': mu_test, 'stdv_test': stdv_test}

    return RMSE_train, R2_train, MAPE_train, RMSE_test, R2_test, MAPE_test


def experiment_ARD(data, y, d, level_sig, train_index, test_index, param_init=[0, 0, 0], RBF=False, plot=False,
                   device=torch.device("cpu"), full=False):
    y_train, y_test = y[train_index], y[test_index]
    x_train, x_test = data[train_index], data[test_index]

    x_train_torch = torch.tensor(x_train, dtype=torch.float64, device=device)
    x_test_torch = torch.tensor(x_test, dtype=torch.float64, device=device)

    if plot:
        sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 1.5})
        fig, axs = plt.subplots(1, 3, figsize=(35, 7))
        axs = axs.ravel()

    if RBF:
        if full:
            model = GP_sig_ARD_full.GP(x_train_torch, torch.tensor(y_train, dtype=torch.float64, device=device),
                                       param_init[0], param_init[1], param_init[2],
                                       param_list=['lengthscale', 'variance', 'noise'], device=device)
        else:
            model = GP_sig_ARD.GP(x_train_torch, torch.tensor(y_train, dtype=torch.float64, device=device), d,
                                  level_sig, param_init[0], param_init[1], param_init[2],
                                  param_list=['lengthscale', 'variance', 'noise'], device=device)
    else:
        if full:
            model = GP_sig_ARD_full.GP(x_train_torch, torch.tensor(y_train, dtype=torch.float64, device=device),
                                       param_init[0], param_init[1], param_init[2],
                                       param_list=['lengthscale', 'noise'], device=device)
        else:
            model = GP_sig_ARD.GP(x_train_torch, torch.tensor(y_train, dtype=torch.float64, device=device), d,
                                  level_sig, param_init[0], param_init[1], param_init[2],
                                  param_list=['lengthscale', 'noise'], device=device)

    if full:
        GP_sig_ARD_full.train(model, 3000, RBF=RBF, plot=plot, ax=axs[0])
        lengthscales = model.transform_softplus(model.lengthscale)
    else:
        GP_sig_ARD.train(model, 3000, RBF=RBF, plot=plot, ax=axs[0])

    mu_test, stdv_test = model.predict(x_test_torch, RBF=RBF)
    mu_train, stdv_train = model.predict_on_training(RBF=RBF)

    R2_train = compute_r2(y_train[:, 0], mu_train[:, 0])
    RMSE_train = compute_rmse(y_train[:, 0], mu_train[:, 0])

    R2_test = compute_r2(y_test[:, 0], mu_test[:, 0])
    RMSE_test = compute_rmse(y_test[:, 0], mu_test[:, 0])

    # ax = plt.figure(figsize=(25, 7))
    # regression_models.plot_fit(axs[0], y_train[:, 0], mu_train[:, 0], std=stdv_train, sklearn=True)

    if plot:
        plot_fit(axs[1], y_train[:, 0], mu_train[:, 0], std=stdv_train, sklearn=True)
        plot_fit(axs[2], y_test[:, 0], mu_test[:, 0], std=stdv_test, sklearn=True)

        plt.show()
    # fig = plt.figure(figsize=(25, 7))
    # regression_models.plot_extrapolation(y_train[:, 0], mu_train[:, 0], stdv_train,y_test[:, 0], mu_test[:, 0], stdv_test)
    # plt.show()
    if full:
        return RMSE_train, R2_train, RMSE_test, R2_test, lengthscales.detach().cpu().numpy()
    else:
        return RMSE_train, R2_train, RMSE_test, R2_test


def plot_fit(ax, y_, pred, low=None, up=None, std=None, sklearn=False):
    left, width = .25, .5
    bottom, height = .25, .5
    right = left + width + .2
    top = bottom + height

    ax.plot(np.linspace(min(y_), max(y_), 20), np.linspace(min(y_), max(y_), 20), linestyle='dashed', color='black')

    order = np.argsort(y_)

    ax.scatter(y_[order], pred[order])

    if sklearn == False:
        y_minus = pred[order] - low[order]
        y_plus = -pred[order] + up[order]

        ax.errorbar(x=y_[order], y=pred[order],
                    yerr=np.concatenate((y_minus[:, None], y_plus[:, None]), axis=1).transpose(), fmt='ok',
                    ecolor='blue', capsize=3)

    else:
        ax.errorbar(x=y_[order], y=pred[order], yerr=std[order], fmt='ok', ecolor='blue', capsize=3)

    RMSE = np.sqrt(np.mean((y_[order] - pred[order]) ** 2))
    num = np.sum((pred[order] - y_[order]) ** 2)

    denum = np.sum((y_[order] - np.mean(y_[order])) ** 2)

    R_squared = 1. - num / denum

    MAPE = np.mean(np.abs(y_[order] - pred[order]) / y_[order])

    ax.set_ylabel('predicted target', fontsize=18)
    ax.set_xlabel('true target', fontsize=18)
    plt.text(right, bottom, 'RMSE=%.3f' % RMSE,
             horizontalalignment='right',
             verticalalignment='bottom',
             transform=ax.transAxes, fontsize=18)
    plt.text(right, bottom - 0.1, 'R-squared=%.3f' % R_squared,
             horizontalalignment='right',
             verticalalignment='bottom',
             transform=ax.transAxes, fontsize=18)

    plt.text(right, bottom - 0.2, 'MAPE=%.3f' % MAPE,
             horizontalalignment='right',
             verticalalignment='bottom',
             transform=ax.transAxes, fontsize=18)


def compute_rmse(y_, pred):
    order = np.argsort(y_)
    return np.sqrt(np.mean((y_[order] - pred[order]) ** 2))


def compute_MAPE(y_, pred):
    order = np.argsort(y_)
    return np.mean(np.abs(y_[order] - pred[order]) / y_[order])


def compute_r2(y_, pred):
    order = np.argsort(y_)
    num = np.sum((pred[order] - y_[order]) ** 2)

    denum = np.sum((y_[order] - np.mean(y_[order])) ** 2)

    return 1. - num / denum



