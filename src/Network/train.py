from U_net import U_NET

import os
import torch
import torchvision
import torch.nn as nn
import torch.optim as opt
import torch.utils.data as ut
import torch.utils.tensorboard as tb

from src.Tools.Tools import *
from src.Data_processing.import_data import *
from src.Data_processing.data_container import *
from src.Data_processing.augment_data import *
from os import path

# Diceloss added as a module to nn
class diceloss(nn.Module):
    def init(self):
        super(diceloss, self).init()

    def forward(self, prediction, target):
        # saving for backwards:
        self.prediction = prediction
        self.target = target

        # diceloss:
        smooth = 1.
        iflat = prediction.view(-1)
        tflat = target.view(-1)
        self.intersection = (iflat * tflat).sum()
        self.sum = torch.sum(iflat * iflat) + torch.sum(tflat * tflat)
        return 1 - ((2. * self.intersection + smooth) / (self.sum + smooth))

    def backward(self, grad_out):
        gt = self.target / self.sum
        inter_over_sum = self.intersection / (self.sum * self.sum)
        pred = self.prediction[:, 1] * inter_over_sum
        dD = gt * 2 + pred * -4

        grad_in = torch.cat((dD*-grad_out[0], dD * grad_out[0]), 0)
        return grad_in, None


# Training
def train(device, epochs, batch_size, loss_function="cross_ent", learn_rate=.001, learn_decay=1e-8, learn_momentum=.99):
    '''
    Trains the network, the training loop is inspired by pytorchs tutorial, see
    https://pytorch.org/tutorials/beginner/blitz/cifar10_tutorial.html
    SummaryWriter https://pytorch.org/docs/stable/tensorboard.html
    '''
    u_net = U_NET(0.1)
    u_net.to(device)

    reps = 5
    augment_and_crop(reps=reps)
    batch_train = Custom_dataset()
    total_size = batch_train.len
    assert(total_size == 30*4+30*reps)
    batch_train, batch_val = random_split(batch_train, [total_size-50, 50])

    dataloader_train = ut.DataLoader(batch_train, batch_size=batch_size,shuffle=True, pin_memory=True)
    dataloader_val = ut.DataLoader(batch_val, batch_size=batch_size, shuffle=True, pin_memory=True)

    len_t = len(dataloader_train)
    len_v = len(dataloader_val)

    # Initilize evaluation and optimizer, optimizer is set to standard-values, might want to change those
    
    if loss_function == "cross_ent":
        evaluation = nn.CrossEntropyLoss()
    elif loss_function == "bce":
        evaluation = nn.BCEWithLogitsLoss()
    elif loss_function == "dice":
        evaluation = diceloss()

    optimizer = opt.SGD(u_net.parameters(), lr=learn_rate, weight_decay=learn_decay, momentum=learn_momentum)
    scheduler = opt.lr_scheduler.ReduceLROnPlateau(optimizer, 'max', patience=2)

    summary = tb.SummaryWriter()

    print(len_t, len_v)

    # Code for saving network
    glob_path = os.path.dirname(os.path.realpath("src"))
    p = os.path.join(glob_path,"saved_nets")

    if not path.exists(p):
        print("saved_nets not found, creating the directory")
        try:
            os.mkdir(p)
        except OSError as exc:
            raise
    else:
        print("saved_nets found")

    #Training loop

    for e in range(epochs):
        print("Epoch: ",e," of ",epochs)
        loss_training = 0

        # Training
        u_net.train()
        pos = 0
        for i in dataloader_train:
            train = i["data"]
            label = i["label"]

            #reset gradients
            optimizer.zero_grad()
            train = train.to(device=device, dtype=torch.float32)
            out = u_net(train)
            #print(out)

            #out = torch.sign(out)

            if pos == len_t-2:
                summary.add_image('training_out',torchvision.utils.make_grid(out), int(pos)+ e * len_t)
                summary.add_image('training_in', torchvision.utils.make_grid(train), int(pos) + e * len_t)
                summary.add_image('training_label', torchvision.utils.make_grid(label), int(pos) + e * len_t)

            label = label.to(device=device, dtype=torch.float32)


            loss = evaluation(out, label)
            loss.backward()
            optimizer.step()

            loss_training += loss.item()
            pos += 1

        loss_training /= len_t
        loss_val = 0

        # Validation
        u_net.eval()
        pos = 0
        for j in dataloader_val:
            val = j["data"]
            label_val = j["label"]
            val = val.to(device=device, dtype=torch.float32)

            with torch.no_grad():
                out = u_net(val)
                if pos == len_v - 2:
                    summary.add_image('val_res', torchvision.utils.make_grid(out) , int(pos) + e * len_v)
                    summary.add_image('val_in', torchvision.utils.make_grid(val), int(pos) + e * len_v)
                    summary.add_image('val_label', torchvision.utils.make_grid(label_val), int(pos) + e * len_v)

                label_val = label_val.to(device=device, dtype=torch.float32)

                #out = torch.sigmoid(out)
                #out = (out > 0.5).float()

                loss = evaluation(out, label_val)
                loss_val += loss.item()
                pos += 1

        loss_val /= len_v

        print("Training loss: ",loss_training)
        print("Validation loss: ", loss_val)

        summary.add_scalar('Loss/train', loss_training, e)
        summary.add_scalar('Loss/val', loss_val, e)

        scheduler.step(loss_val)
        if epochs % 100 == 0:
            torch.save(u_net.state_dict(), p + '/save'+str(e)+'pt')
        # print(torch.cuda.memory_summary(device=None, abbreviated=False))

    summary.flush()
    summary.close()

    print("Saving network")
    torch.save(u_net.state_dict(), p+'/save.pt')