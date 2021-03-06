import numpy as np
from skimage.metrics import structural_similarity as ssim
import matplotlib.pyplot as plt
from skimage.metrics import (adapted_rand_error,
                              variation_of_information)

def split_to_training_and_validation(dataset, labels, percent_to_train, percent_to_test):
    assert len(dataset) == len(labels)
    index = np.arange(len(dataset))
    np.random.shuffle(index)

    to_train = int(len(dataset)*percent_to_train)
    to_test = int(len(dataset) * percent_to_test) + to_train
    training = []
    labels_tr = []
    validation = []
    labels_vl = []
    test = []
    labels_test = []

    for i in range(len(dataset)):
        if i <= to_train:
            training.append(dataset[index[i]])
            labels_tr.append(labels[index[i]])
        elif i <= to_test:
            test.append(dataset[index[i]])
            labels_test.append(labels[index[i]])
        else:
            validation.append(dataset[index[i]])
            labels_vl.append(labels[index[i]])

    return training, labels_tr, validation, labels_vl, test, labels_test
'''
def rand_error(prediction, target):
    
    
    
    iflat = prediction.view(-1)
    tflat = target.view(-1)
    true_positive = 0
    true_negative = 0
    n = len(iflat)
    for i in range(n):
        if iflat[i] == 1 and tflat[i] == 1:
            true_positive += 1
        elif iflat[i] == 0 and tflat[i] == 0:
            true_negative += 1
    return 1 - (true_positive+true_negative) / (n*(n-1)/2)
'''
'''
def rand_error_2(prediction, target):
    # Using the formula from here: https://imagej.net/Rand_error
    assert len(prediction) == len(target)
    assert len(prediction[0]) == len(target[0])
    n = len(prediction)*len(prediction[0])
    a = 0
    b = 0
    pred = prediction.flatten()
    targ = target.flatten()
    print(pred)
    for i in range(len(pred)):
        for j in range(i):
            if pred[i] == pred[j] and targ[i] == targ[j]:
                a+=1
            elif pred[i] != pred[0][j] and targ[i] != targ[j]:
                b+=1
    d = (n*(n-1))/2
    return 1 - ((a+b)/d)
'''

def rand_error_3(prediction, target):
    return adapted_rand_error(prediction, target)

def IOU(component1, component2):
    overlap = component1 * component1  # Logical AND
    union = component1 + component2  # Logical OR

    IOU = overlap.sum() / float(union.sum())
    return IOU
  
def pixel_error(prediction, target):
    # Images needs to be in same size
    mse_error = np.sum((prediction.astype("float") - target.astype("float")) ** 2)
    mse_error /= float(prediction.shape[0] * target.shape[1])
    s = ssim(prediction, target, data_range=255)
    return mse_error, s

def print_img(m, s, A, B, title, path):
    fig = plt.figure(title)
    plt.suptitle("MSE: %.2f, SSIM: %.2f" % (m, s))
    # show first image
    fig.add_subplot(1, 2, 1)
    plt.imshow(A, cmap = plt.cm.gray)
    plt.axis("off")
    # show the second image
    fig.add_subplot(1, 2, 2)
    plt.imshow(B, cmap = plt.cm.gray)
    plt.axis("off")
    # show the images
    plt.savefig(path+'/'+title+'.png')
