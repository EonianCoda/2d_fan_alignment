import torch
import torch.nn as nn
import torch.nn.functional as F
from model.utils import conv1x1, conv3x3
from model.utils import HPM_ConvBlock, SELayer

class HourGlassNet(nn.Module):
    def __init__(self, depth:int, num_feats:int, resBlock=HPM_ConvBlock, use_SE=False):
        super(HourGlassNet, self).__init__()
        self.depth = depth
        self.num_feats = num_feats

        self.use_SE = use_SE
        self.downsample = nn.AvgPool2d(kernel_size=2, stride=2)
        for level in range(1, depth + 1):
            # upper branch
            self.add_module(f"shortcut{level}", resBlock(self.num_feats, self.num_feats))
            # lower branch
            self.add_module(f"conv{level}_1", resBlock(self.num_feats, self.num_feats))
            self.add_module(f"conv{level}_2", resBlock(self.num_feats, self.num_feats))

            if use_SE:
                self.add_module(f"SE{level}", SELayer(self.num_feats))

            if level == depth:
                self.add_module(f"conv_middle", resBlock(self.num_feats, self.num_feats))

    def _forward(self, x, level:int):
        residual = x
        # upper branch
        residual = self._modules[f"shortcut{level}"](residual)
        # lower branch
        x = self.downsample(x)
        x = self._modules[f"conv{level}_1"](x)
        
        if level == self.depth:
            # End recursion
            x = self._modules["conv_middle"](x)
        else:
            # Recursion forward
            x = self._forward(x, level + 1)

        x = self._modules[f"conv{level}_2"](x)
        if self.use_SE:
            x = self._modules[f"SE{level}"](x)
        x = F.interpolate(x, scale_factor=2, mode='nearest')

        return x + residual

    def forward(self, x):
        return self._forward(x, 1)

class FAN(nn.Module):
    """Facial Alignment network
    """
    def __init__(self, num_HG:int = 4, HG_depth:int = 4, num_feats:int = 256, 
                num_classes:int = 68, resBlock=HPM_ConvBlock, use_SE=False):
        super(FAN, self).__init__()
        self.num_HG = num_HG # num of how many hourglass stack
        self.HG_dpeth = HG_depth # num of recursion in hourglass net
        self.num_feats = num_feats
        self.num_classes = num_classes # num of keypoints

        # Base part
        self.relu = nn.ReLU(inplace=True)
        self.max_pool2d = nn.MaxPool2d(kernel_size=2, stride=2)

        self.conv1 = nn.Conv2d(3, self.num_feats // 4, kernel_size=7, stride=2, padding=3)
        self.bn1 = nn.BatchNorm2d(self.num_feats // 4)
        self.conv2 = resBlock(self.num_feats // 4, self.num_feats // 2)
        self.conv3 = resBlock(self.num_feats // 2, self.num_feats // 2)
        self.conv4 = resBlock(self.num_feats // 2, self.num_feats)

        # Stacked hourglassNet part
        for stack_idx in range(1, self.num_HG + 1):
            self.add_module(f"HG{stack_idx}", HourGlassNet(self.HG_dpeth, self.num_feats, resBlock=resBlock, use_SE=use_SE))
            self.add_module(f"stack{stack_idx}_conv1", resBlock(self.num_feats, self.num_feats))
            self.add_module(f"stack{stack_idx}_conv2", conv1x1(self.num_feats, self.num_feats))
            self.add_module(f"stack{stack_idx}_bn1", nn.BatchNorm2d(int(self.num_feats)))

            self.add_module(f"stack{stack_idx}_conv_out", conv1x1(self.num_feats, self.num_classes))
            if stack_idx != self.num_HG:
                self.add_module(f"stack{stack_idx}_conv3", conv1x1(self.num_feats, self.num_feats))
                self.add_module(f"stack{stack_idx}_shortcut", conv1x1(self.num_classes, self.num_feats))
        self._weight_init()
    def _weight_init(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                m.weight.data.normal_(0, 0.01)
                m.bias.data.zero_()
    def forward(self, x):
        outputs = []
        # Base part
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.conv2(x)
        x = self.max_pool2d(x)
        x = self.conv3(x)
        x = self.conv4(x)

        # Stacked hourglassNet part
        for stack_idx in range(1, self.num_HG + 1):
            if stack_idx != self.num_HG:
                residual = x
            x = self._modules[f"HG{stack_idx}"](x)
            x = self._modules[f"stack{stack_idx}_conv1"](x)
            x = self._modules[f"stack{stack_idx}_conv2"](x)
            x = self.relu(self._modules[f"stack{stack_idx}_bn1"](x))
            # Output heatmap
            out = self._modules[f"stack{stack_idx}_conv_out"](x)
            outputs.append(out)
            # lower and upper branch
            if stack_idx != self.num_HG:
                x = self._modules[f"stack{stack_idx}_conv3"](x)
                out_ = self._modules[f"stack{stack_idx}_shortcut"](out)
                x = out_ + residual + x
        return outputs
