
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import _LRScheduler, ReduceLROnPlateau
import numpy as np
from tqdm import tqdm
import random
import os
import time


class Warmup_ReduceLROnPlateau(_LRScheduler):
    def __init__(self, optimizer, warm_up_epoch, patience=3, verbose=True):
        self.warm_up_epoch = warm_up_epoch
        self.cur_epoch = 0
        self.after_scheduler = ReduceLROnPlateau(optimizer, patience=patience)
        self.verbose = verbose
        super().__init__(optimizer)
        self.last_epoch = 0

    def get_lr(self) -> float:
        if self.last_epoch < self.warm_up_epoch:
            return [base_lr * (float(self.last_epoch + 1) / self.warm_up_epoch) for base_lr in self.base_lrs]
        else:
            return self.after_scheduler._last_lr

    def _print_info(self):
        for group_idx, lr in enumerate(self.get_lr()):
            print("Epoch {:4d}: Adjusting learning rate of group {} to {:4e}.".format(self.last_epoch, group_idx, lr))

    def step(self,metric=None):
        cur_lr = self.get_lr()
        self.last_epoch = 1 if self.last_epoch == 0 else self.last_epoch + 1
        if self.last_epoch < self.warm_up_epoch:
            for param_group, lr in zip(self.optimizer.param_groups, self.get_lr()):
                param_group['lr'] = lr
        elif metric != None:
            self.after_scheduler.step(metric)
        else:
            raise ValueError("Currnet epoch is larger than warm up epoch and metirc still is None")
        if self.verbose and cur_lr != self.get_lr():
            self._print_info()

def fixed_seed(myseed):
    np.random.seed(myseed)
    random.seed(myseed)
    torch.manual_seed(myseed)

    torch.backends.cudnn.benchmark = True
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(myseed)
        torch.cuda.manual_seed(myseed)


def train(model, train_loader, val_loader, epoch:int, save_path:str, device, criterion, scheduler, optimizer):
    start_train = time.time()

    overall_loss = []
    overall_val_loss = []


    for epoch in range(epoch):
        print(f'epoch = {epoch}')
        # epcoch setting
        start_time = time.time()
        train_loss = 0.0

        # training part
        # start training
        model.train()
        for batch_idx, (data, label) in enumerate(tqdm(train_loader)):
            data = data.to(device)
            label = label.to(device)

            outputs = model(data) 
            # intermediate supervision
            loss = 0
            for output in outputs:
                loss += criterion(output, label)

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm= 5.)
            optimizer.step()

            train_loss += loss.item()
            del loss
  
        train_loss = train_loss / len(train_loader.dataset)     
        overall_loss.append(float(train_loss))
        # validation part 
        with torch.no_grad():
            model.eval()
            val_loss = 0
            
            for batch_idx, (data, label) in enumerate(tqdm(val_loader)):
                data = data.to(device)
                label = label.to(device)

                outputs = model(data)
                # intermediate supervision
                loss = 0
                for output in outputs:
                    loss += criterion(output, label)
                val_loss += loss
                
            val_loss /= len(val_loader.dataset)
            
            overall_val_loss.append(float(val_loss))

        # Scheduler
        scheduler.step(val_loss)

        # Display the results
        end_time = time.time()
        elp_time = end_time - start_time
        min = elp_time // 60 
        sec = elp_time % 60
        print('*'*10)
        print('time = {:.4f} MIN {:.4f} SEC, total time = {:.4f} Min {:.4f} SEC '.format(elp_time // 60, elp_time % 60, (end_time-start_train) // 60, (end_time-start_train) % 60))
        print(f'training loss : {train_loss:.4f} ', )
        print(f'val loss : {val_loss:.4f} ')
        print('========================\n')


        torch.save(model.state_dict(), os.path.join(save_path, f'{epoch}.pt'))
