cfg = {
    ### Loss type ###  
    'loss_idx': 5,
    'losses': {0:"L2",
                1:"L1",
                2:"smoothL1",
                3:"wing_loss",
                4:"adaptive_wing_loss",
                5:"weighted_L2"},

    ### Data Balance ###
    'balance_data': False,
    ### Scheduler setting ###
    'scheduler_type': 1,  # 0: ReduceLROnPlateau, 1: Warmup_ReduceLROnPlateau 
    'warm_step': 2,   # If scheduler == 1, then use warm_epoch arg
    'patience': 3,

    ### Model arichitecture ###
    'num_HG': 2,
    'HG_depth':4,
    'num_feats':128,
    'fix_coord':True,
    ### Attention Block ###
    'attention_block_idx': 1,
    'attention_blocks': {0: "None",
                        1: "SELayer",
                        2: "CA_Block"},

    ### Augumentation Setting ###
    'aug_setting':{'flip': False,
                'rotation': True,
                'noise': False,
                'gaussianBlur': False,
                'colorJitter': False,
                'grayscale': False},                    
    ### Optimizer Type ###  
    'optimizer_idx': 0,
    'optimizers': {0: "RMSprop",
                    1: "SGD",
                    2: "Adam",
                    3: "AdamW"},
    ### Resdiual Block ###
    'resBlock_idx': 0,
    'resBlocks': {0: "HPM_ConvBlock",
                1: "Bottleneck",
                2: "InvertedResidual"},
    ### Training hyperparameters ###
    'batch_size': 8,
    'lr':1e-4,
    'epoch':20,
    ### training setting ##
    'train_annot':'./data/train_annot.pkl',
    'train_data_root':'./data/train',
    'split_ratio': 0.9,
    ### testing data ##
    'test_annot':'./data/val_annot.pkl',
    'test_data_root':'./data/val',
    
    'seed': 987,
}
