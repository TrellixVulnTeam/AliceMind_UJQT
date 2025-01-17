# Copyright 2019-present NAVER Corp.
# Apache License v2.0

# Wonseok Hwang

import os, json
import random as rd
from copy import deepcopy
import difflib

import re
import torch
import torchvision.datasets as dsets
import torch.nn as nn
import torch.nn.functional as F
from matplotlib.pylab import *
from torch.autograd import Variable

from .utils import generate_perm_inv
from .utils import json_default_type_checker

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load data -----------------------------------------------------------------------------------------------
def load_wikisql(path_wikisql, toy_model, toy_size, bert=False, no_w2i=False, no_hs_tok=False, aug=False):
    # Get data
    train_data, train_table = load_wikisql_data(path_wikisql, mode='train', toy_model=toy_model, toy_size=toy_size,
                                                no_hs_tok=no_hs_tok, aug=aug)
    dev_data, dev_table = load_wikisql_data(path_wikisql, mode='dev', toy_model=toy_model, toy_size=toy_size,
                                            no_hs_tok=no_hs_tok)

    # Get word vector
    if no_w2i:
        w2i, wemb = None, None
    else:
        w2i, wemb = load_w2i_wemb(path_wikisql, bert)

    return train_data, train_table, dev_data, dev_table, w2i, wemb


def load_nl2sql(path_nl2sql, toy_model, toy_size, bert=False, no_w2i=True, no_hs_tok=False, aug=False):
    # Get data
    train_data, train_table = load_nl2sql_data(path_nl2sql, mode='train', toy_model=toy_model, toy_size=toy_size,
                                               no_hs_tok=no_hs_tok, aug=aug)
    ############ here!
    dev_data, dev_table = load_nl2sql_data(path_nl2sql, mode='val', toy_model=toy_model, toy_size=toy_size,
                                           no_hs_tok=no_hs_tok)
    for k, v in train_table.items():
        print(v)
        break

    # Get word vector
    if no_w2i:
        w2i, wemb = None, None
    else:
        w2i, wemb = load_w2i_wemb(path_nl2sql, bert)

    return train_data, train_table, dev_data, dev_table, w2i, wemb


def load_nl2sql_data(path_nl2sql, mode='train', toy_model=False, toy_size=10, no_hs_tok=False, aug=False, path_sql1=None):
    """ Load training sets
    """
    if aug:
        mode = f"aug.{mode}"
        print('Augmented data is loaded!')

    sub_dir = mode  # here!!!!!!!
    if mode == 'train' or mode == 'val':
        path_sql = os.path.join(path_nl2sql, sub_dir, mode + '_wvi.json')  #######################
    else:
        path_sql = os.path.join(path_nl2sql, sub_dir, mode + '.json')
        # path_sql = os.path.join(path_nl2sql, sub_dir, mode+'_wvi.json')

    if path_sql1 is not None:
        path_sql = path_sql1
    # print(path_sql)
    path_table = os.path.join(path_nl2sql, sub_dir, mode + '.tables.json')

    data = []
    table = {}
    with open(path_sql, encoding='utf-8') as f:
        for idx, line in enumerate(f):
            if toy_model and idx >= toy_size:
                break
            # print(line)
            t1 = json.loads(line)
            data.append(t1)

    with open(path_table, encoding='utf-8') as f:
        for idx, line in enumerate(f):
            if toy_model and idx > toy_size:
                break

            t1 = json.loads(line.strip())
            table[t1['id']] = t1

    return data, table


def load_wikisql_data(path_wikisql, mode='train', toy_model=False, toy_size=10, no_hs_tok=False, aug=False):
    """ Load training sets
    """
    if aug:
        mode = f"aug.{mode}"
        print('Augmented data is loaded!')

    path_sql = os.path.join(path_wikisql, mode + '_tok.jsonl')
    if no_hs_tok:
        path_table = os.path.join(path_wikisql, mode + '.tables.jsonl')
    else:
        path_table = os.path.join(path_wikisql, mode + '_tok.tables.jsonl')

    data = []
    table = {}
    with open(path_sql) as f:
        for idx, line in enumerate(f):
            if toy_model and idx >= toy_size:
                break

            t1 = json.loads(line.strip())
            data.append(t1)

    with open(path_table) as f:
        for idx, line in enumerate(f):
            if toy_model and idx > toy_size:
                break

            t1 = json.loads(line.strip())
            table[t1['id']] = t1

    return data, table


def load_w2i_wemb(path_wikisql, bert=False):
    """ Load pre-made subset of TAPI.
    """
    if bert:
        with open(os.path.join(path_wikisql, 'w2i_bert.json'), 'r') as f_w2i:
            w2i = json.load(f_w2i)
        wemb = load(os.path.join(path_wikisql, 'wemb_bert.npy'), )
    else:
        with open(os.path.join(path_wikisql, 'w2i.json'), 'r') as f_w2i:
            w2i = json.load(f_w2i)

        wemb = load(os.path.join(path_wikisql, 'wemb.npy'), )
    return w2i, wemb



def temp_func(x):
    return x


def get_loader_wikisql(data_train, data_dev, bS, shuffle_train=True, shuffle_dev=False):
    train_loader = torch.utils.data.DataLoader(
        batch_size=bS,
        dataset=data_train,
        shuffle=shuffle_train,
        num_workers=1,
        collate_fn=temp_func  # now dictionary values are not merged!
    )

    dev_loader = torch.utils.data.DataLoader(
        batch_size=bS,
        dataset=data_dev,
        shuffle=shuffle_dev,
        num_workers=1,
        collate_fn=temp_func  # now dictionary values are not merged!
    )

    return train_loader, dev_loader


def get_fields_info(t1s, tables, train=True):
    nlu, nlu_t, sql_i, tb, hs_t = [], [], [], [], []
    for t1 in t1s:
        nlu.append(t1['question'])
        nlu_t.append(t1['question_tok'])
        hs_t.append(t1['header_tok'])
        if train:
            sql_i.append(t1['sql'])
            tb.append(tables[t1['table_id']])

    return nlu, nlu_t, sql_i, tb, hs_t

def get_fields_1(t1, tables, no_hs_t=False, no_sql_t=True, testt=False):
    nlu1 = t1['question']
    # nlu_t1 = t1['question']
    nlu_t1 = t1['question_tok']
    tid1 = t1['table_id']


    if not testt:
        sql_i1 = t1['sql']
        sql_q1 = t1['sql']
    else:
        sql_i1 = None
        sql_q1 = None

    if no_sql_t:
        sql_t1 = None
    else:
        sql_t1 = t1['query_tok']

    tb1 = tables[tid1]
    # print(tid1)
    # print(tb1['header'])

    if not no_hs_t:
        hs_t1 = tb1['header_tok']
    else:
        hs_t1 = []
    hs1 = tb1['header']

    return nlu1, nlu_t1, tid1, sql_i1, sql_q1, sql_t1, tb1, hs_t1, hs1


def get_fields(t1s, tables, no_hs_t=False, no_sql_t=False, testt=False):
    nlu, nlu_t, tid, sql_i, sql_q, sql_t, tb, hs_t, hs = [], [], [], [], [], [], [], [], []
    for t1 in t1s:
        if no_hs_t:
            nlu1, nlu_t1, tid1, sql_i1, sql_q1, sql_t1, tb1, hs_t1, hs1 = get_fields_1(t1, tables, no_hs_t, no_sql_t,
                                                                                       testt=testt)
        else:
            nlu1, nlu_t1, tid1, sql_i1, sql_q1, sql_t1, tb1, hs_t1, hs1 = get_fields_1(t1, tables, no_hs_t, no_sql_t,
                                                                                       testt=testt)

        nlu.append(nlu1)
        nlu_t.append(nlu_t1)
        tid.append(tid1)
        sql_i.append(sql_i1)
        sql_q.append(sql_q1)
        sql_t.append(sql_t1)

        tb.append(tb1)
        hs_t.append(hs_t1)
        hs.append(hs1)

    return nlu, nlu_t, sql_i, sql_q, sql_t, tb, hs_t, hs


# Embedding -------------------------------------------------------------------------

def word_to_idx1(words1, w2i, no_BE):
    w2i_l1 = []
    l1 = len(words1)  # +2 because of <BEG>, <END>

    for w in words1:
        idx = w2i.get(w, 0)
        w2i_l1.append(idx)

    if not no_BE:
        l1 += 2
        w2i_l1 = [1] + w2i_l1 + [2]

    return w2i_l1, l1


def words_to_idx(words, w2i, no_BE=False):
    """
    Input: [ ['I', 'am', 'hero'],
             ['You', 'are 'geneus'] ]
    output:

    w2i =  [ B x max_seq_len, 1]
    wemb = [B x max_seq_len, dim]

    - Zero-padded when word is not available (teated as <UNK>)
    """
    bS = len(words)
    l = torch.zeros(bS, dtype=torch.long).to(device)  # length of the seq. of words.
    w2i_l_list = []  # shall be replaced to arr

    #     wemb_NLq_batch = []

    for i, words1 in enumerate(words):
        w2i_l1, l1 = word_to_idx1(words1, w2i, no_BE)
        w2i_l_list.append(w2i_l1)
        l[i] = l1

    # Prepare tensor of wemb
    # overwrite w2i_l
    w2i_l = torch.zeros([bS, int(max(l))], dtype=torch.long).to(device)
    for b in range(bS):
        w2i_l[b, :l[b]] = torch.LongTensor(w2i_l_list[b]).to(device)

    return w2i_l, l


def hs_to_idx(hs_t, w2i, no_BE=False):
    """ Zero-padded when word is not available (teated as <UNK>)
    Treat each "header tokens" as if they are NL-utterance tokens.
    """

    bS = len(hs_t)  # now, B = B_NLq
    hpu_t = []  # header pseudo-utterance
    l_hs = []
    for hs_t1 in hs_t:
        hpu_t += hs_t1
        l_hs1 = len(hs_t1)
        l_hs.append(l_hs1)

    w2i_hpu, l_hpu = words_to_idx(hpu_t, w2i, no_BE=no_BE)
    return w2i_hpu, l_hpu, l_hs


# Encoding ---------------------------------------------------------------------

def encode(lstm, wemb_l, l, return_hidden=False, hc0=None, last_only=False, U=None, V=None, ctx=None, l_hs=None):
    """ [batch_size, max token length, dim_emb]
    """
    bS, mL, eS = wemb_l.shape

    # sort before packking
    l = array(l)
    perm_idx = argsort(-l)
    perm_idx_inv = generate_perm_inv(perm_idx)

    # pack sequence

    packed_wemb_l = nn.utils.rnn.pack_padded_sequence(wemb_l[perm_idx, :, :],
                                                      l[perm_idx],
                                                      batch_first=True)

    # Time to encode
    if hc0 is not None:
        hc0 = (hc0[0][:, perm_idx], hc0[1][:, perm_idx])

    # ipdb.set_trace()
    packed_wemb_l = packed_wemb_l.float()  # I don't know why..
    packed_wenc, hc_out = lstm(packed_wemb_l, hc0)
    hout, cout = hc_out

    # unpack
    wenc, _l = nn.utils.rnn.pad_packed_sequence(packed_wenc, batch_first=True)

    if last_only:
        if ctx is None:
            # Take only final outputs for each columns.
            wenc = wenc[tuple(range(bS)), l[perm_idx] - 1]  # [batch_size, dim_emb]
            wenc.unsqueeze_(1)  # [batch_size, 1, dim_emb]
        else:
            ctx = ctx.unsqueeze(1)
            # [batch_size, 1, dim_emb] -> [batch_size, 1, hS]
            wenc_u = U(ctx)
            # [batch_size, seq_len, dim_emb] -> [batch_size, seq_len, hS]
            wenc_v = V(wenc)
            start = 0
            # [batch_size, 1, dim_emb]
            wenc2 = torch.zeros(wenc.shape[0], 1, wenc.shape[2])
            for b in range(ctx.shape[0]):
                # [1, hS] * [batch_size, seq_len, hS] -> [batch_size, seq_len, hS]
                attn = torch.mul(wenc_u[b], wenc_v[start:start + l_hs[b]])
                # attn, _ = nn.utils.rnn.pad_packed_sequence(attn, batch_first=True)
                # [batch_size, seq_len]
                attn = F.softmax(attn.sum(2), dim=1)
                wenc1 = torch.bmm(attn.unsqueeze(1), wenc[start:start + l_hs[b]])
                wenc1 += ctx[b]
                wenc2[start:start + l_hs[b]] = wenc1
                start += l_hs[b]
            wenc = wenc2

    wenc = wenc[perm_idx_inv]

    if return_hidden:
        # hout.shape = [number_of_directoin * num_of_layer, seq_len(=batch size), dim * number_of_direction ] w/ batch_first.. w/o batch_first? I need to see.
        hout = hout[:, perm_idx_inv].to(device)
        cout = cout[:, perm_idx_inv].to(device)  # Is this correct operation?

        return wenc, hout, cout
    else:
        return wenc


def encode_hpu(lstm, wemb_hpu, l_hpu, l_hs, U=None, V=None, ctx=None):
    # print('weemb before lstm:', wemb_hpu.shape)
    wenc_hpu, hout, cout = encode(lstm,
                                  wemb_hpu,
                                  l_hpu,
                                  return_hidden=True,
                                  hc0=None,
                                  last_only=True,
                                  U=U,
                                  V=V,
                                  ctx=ctx,
                                  l_hs=l_hs)
    # print("wenc_hpu:", wenc_hpu.shape)
    wenc_hpu = wenc_hpu.squeeze(1)
    bS_hpu, mL_hpu, eS = wemb_hpu.shape
    hS = wenc_hpu.size(-1)
    # print('l hs:', l_hs)

    wenc_hs = wenc_hpu.new_zeros(len(l_hs), max(l_hs), hS)
    wenc_hs = wenc_hs.to(device)
    # print('wenc hs:', wenc_hs.shape)

    # Re-pack according to batch.
    # ret = [B_NLq, max_len_headers_all, dim_lstm]
    st = 0
    for i, l_hs1 in enumerate(l_hs):
        wenc_hs[i, :l_hs1] = wenc_hpu[st:(st + l_hs1)]
        st += l_hs1

    return wenc_hs


# Statistics -------------------------------------------------------------------------------------------------------------------


def get_wc1(conds):
    """
    [ [wc, wo, wv],
      [wc, wo, wv], ...
    ]
    """
    wc1 = []
    for cond in conds:
        wc1.append(int(cond[0]))
    return wc1


def get_wo1(conds):
    """
    [ [wc, wo, wv],
      [wc, wo, wv], ...
    ]
    """
    wo1 = []
    for cond in conds:
        wo1.append(int(cond[1]))
    return wo1


def get_wv1(conds):
    """
    [ [wc, wo, wv],
      [wc, wo, wv], ...
    ]
    """
    wv1 = []
    for cond in conds:
        wv1.append(str(cond[2]))
    return wv1


def get_g(sql_i):
    """ for backward compatibility, separated with get_g"""
    g_sc = []
    g_sa = []
    g_wn = []
    g_wc = []
    g_wo = []
    g_wv = []
    g_slen = []
    # tiaojian lianjie and/or
    g_cond_conn_op = []
    idxs = []
    for b, psql_i1 in enumerate(sql_i):
        # print('sqlooiiiii:', psql_i1)
        # 暂不考虑选两个列和选两个聚合函数的情况
        # here!!!!!!!!!!!!!
        # g_sc.append(psql_i1["sel"][0])
        # g_sa.append(psql_i1["agg"][0])
        psql_i1["sel"] = np.asarray(psql_i1["sel"])
        idx = np.argsort(psql_i1["sel"])
        g_sc.append(list(psql_i1["sel"][idx]))
        g_sa.append(list(np.asarray(psql_i1["agg"])[idx]))
        g_slen.append(len(psql_i1["sel"]))
        psql_i1["sel"] = np.sort(psql_i1["sel"])
        psql_i1["agg"] = np.sort(psql_i1["agg"])
        assert len(psql_i1["sel"]) == len(psql_i1["agg"])

        g_cond_conn_op.append(psql_i1["cond_conn_op"])

        conds = np.asarray(psql_i1['conds'])
        conds_num = [int(x) for x in conds[:, 0]]
        idx = np.argsort(conds_num)
        idxs.append(idx)
        psql_i1['conds'] = conds[idx]
        if not len(psql_i1["agg"]) < 0:
            g_wn.append(len(conds))
            g_wc.append(get_wc1(list(conds[idx])))
            g_wo.append(get_wo1(list(conds[idx])))
            g_wv.append(get_wv1(list(conds[idx])))
        else:
            raise EnvironmentError
    return g_sc, g_sa, g_wn, g_wc, g_wo, g_wv, g_cond_conn_op, g_slen, idxs


def get_g_wvi_corenlp(t, idxs):
    g_wvi = []
    for b, t1 in enumerate(t):
        g_wvi1 = []
        for g_wvi_corenlp11 in list(np.asarray(t1['wvi_corenlp'])[idxs[b]]):
            st_idx, ed_idx = g_wvi_corenlp11
            g_wvi11 = [st_idx, ed_idx]
            g_wvi1.append(g_wvi11)
        g_wvi.append(g_wvi1)
    
    return g_wvi


def update_w2i_wemb(word, wv, idx_w2i, n_total, w2i, wemb):
    """ Follow same approach from SQLNet author's code.
        Used inside of generaet_w2i_wemb.
    """

    # global idx_w2i, w2i, wemb  # idx, word2vec, word to idx dictionary, list of embedding vec, n_total: total number of words
    if (word in wv) and (word not in w2i):
        idx_w2i += 1
        w2i[word] = idx_w2i
        wemb.append(wv[word])
    n_total += 1
    return idx_w2i, n_total


def make_w2i_wemb(args, path_save_w2i_wemb, wv, data_train, data_dev, data_test, table_train, table_dev, table_test):
    w2i = {'<UNK>': 0, '<BEG>': 1, '<END>': 2}  # to use it when embeds NL query.
    idx_w2i = 2
    n_total = 3

    wemb = [np.zeros(300, dtype=np.float32) for _ in range(3)]  # 128 is of TAPI vector.
    idx_w2i, n_total = generate_w2i_wemb(data_train, wv, idx_w2i, n_total, w2i, wemb)
    idx_w2i, n_total = generate_w2i_wemb_table(table_train, wv, idx_w2i, n_total, w2i, wemb)

    idx_w2i, n_total = generate_w2i_wemb(data_dev, wv, idx_w2i, n_total, w2i, wemb)
    idx_w2i, n_total = generate_w2i_wemb_table(table_dev, wv, idx_w2i, n_total, w2i, wemb)

    idx_w2i, n_total = generate_w2i_wemb(data_test, wv, idx_w2i, n_total, w2i, wemb)
    idx_w2i, n_total = generate_w2i_wemb_table(table_test, wv, idx_w2i, n_total, w2i, wemb)

    path_w2i = os.path.join(path_save_w2i_wemb, 'w2i.json')
    path_wemb = os.path.join(path_save_w2i_wemb, 'wemb.npy')

    wemb = np.stack(wemb, axis=0)

    with open(path_w2i, 'w') as f_w2i:
        json.dump(w2i, f_w2i)

    np.save(path_wemb, wemb)

    return w2i, wemb


def generate_w2i_wemb_table(tables, wv, idx_w2i, n_total, w2i, wemb):
    """ Generate subset of GloVe
        update_w2i_wemb. It uses wv, w2i, wemb, idx_w2i as global variables.

        To do
        1. What should we do with the numeric?
    """
    # word_set from NL query
    for table_id, table_contents in tables.items():

        # NLq = t1['question']
        # word_tokens = NLq.rstrip().replace('?', '').split(' ')
        headers = table_contents['header_tok']  # [ ['state/terriotry'], ['current', 'slogan'], [],
        for header_tokens in headers:
            for token in header_tokens:
                idx_w2i, n_total = update_w2i_wemb(token, wv, idx_w2i, n_total, w2i, wemb)
                # WikiSQL generaets unbelivable query... using state/territory in the NLq. Unnatural.. but as is
                # when there is slash, unlike original SQLNet which treats them as single token, we use
                # both tokens. e.g. 'state/terriotry' -> 'state'
                # token_spl = token.split('/')
                # for token_spl1 in token_spl:
                #         idx_w2i, n_total = update_w2i_wemb(token_spl1, wv, idx_w2i, n_total, w2i, wemb)

    return idx_w2i, n_total


def generate_w2i_wemb(train_data, wv, idx_w2i, n_total, w2i, wemb):
    """ Generate subset of GloVe
        update_w2i_wemb. It uses wv, w2i, wemb, idx_w2i as global variables.

        To do
        1. What should we do with the numeric?
    """
    # word_set from NL query
    for i, t1 in enumerate(train_data):
        # NLq = t1['question']
        # word_tokens = NLq.rstrip().replace('?', '').split(' ')
        word_tokens = t1['question_tok']
        # Currently, TAPI does not use "?". So, it is removed.
        for word in word_tokens:
            idx_w2i, n_total = update_w2i_wemb(word, wv, idx_w2i, n_total, w2i, wemb)
            n_total += 1

    return idx_w2i, n_total


def generate_w2i_wemb_e2k_headers(e2k_dicts, wv, idx_w2i, n_total, w2i, wemb):
    """ Generate subset of TAPI from english-to-korean dict of table headers etc..
        update_w2i_wemb. It uses wv, w2i, wemb, idx_w2i as global variables.

        To do
        1. What should we do with the numeric?
           Current version do not treat them specially. But this would be modified later so that we can use tags.
    """
    # word_set from NL query
    for table_name, e2k_dict in e2k_dicts.items():
        word_tokens_list = list(e2k_dict.values())
        # Currently, TAPI does not use "?". So, it is removed.
        for word_tokens in word_tokens_list:
            for word in word_tokens:
                idx_w2i, n_total = update_w2i_wemb(word, wv, idx_w2i, n_total, w2i, wemb)
                n_total += 1

    return idx_w2i, n_total


# BERT =================================================================================================================
def tokenize_nlu1(tokenizer, nlu1):
    nlu1_tok = tokenizer.tokenize(nlu1)
    return nlu1_tok


def tokenize_hds1(tokenizer, hds1):
    hds_all_tok = []
    for hds11 in hds1:
        sub_tok = tokenizer.tokenize(hds11)
        hds_all_tok.append(sub_tok)

def generate_inputs(tokenizer, nlu1_tok, hds1):
    tokens = []
    segment_ids = []

    tokens.append("[CLS]")
    i_st_nlu = len(tokens)  # to use it later

    segment_ids.append(1)
    for token in nlu1_tok:
        tokens.append(token)
        segment_ids.append(1)
    i_ed_nlu = len(tokens)
    tokens.append("[SEP]")
    segment_ids.append(1)

    i_hds = []
    # for doc
    for i, hds11 in enumerate(hds1):
        i_st_hd = len(tokens)
        sub_tok = tokenizer.tokenize(hds11)
        tokens += sub_tok
        i_ed_hd = len(tokens)
        i_hds.append((i_st_hd, i_ed_hd))
        segment_ids += [2] * len(sub_tok)
        if i < len(hds1) - 1:
            tokens.append("[SEP]")
            segment_ids.append(2)
        elif i == len(hds1) - 1:
            tokens.append("[SEP]")
            segment_ids.append(2)
        else:
            raise EnvironmentError

    i_nlu = (i_st_nlu, i_ed_nlu)

    return tokens, segment_ids, i_nlu, i_hds


def gen_l_hpu(i_hds):
    """
    # Treat columns as if it is a batch of natural language utterance with batch-size = # of columns * # of batch_size
    i_hds = [(17, 18), (19, 21), (22, 23), (24, 25), (26, 29), (30, 34)])
    """
    l_hpu = []
    for i_hds1 in i_hds:
        for i_hds11 in i_hds1:
            l_hpu.append(i_hds11[1] - i_hds11[0])

    return l_hpu


def get_bert_output_s2s(model_bert, tokenizer, nlu_t, hds, sql_vocab, max_seq_length):
    """
    s2s version. Treat SQL-tokens as pseudo-headers
    sql_vocab = ("sql select", "sql where", "sql and", "sql equal", "sql greater than", "sql less than")

    e.g.)
    Q: What is the name of the player with score greater than 15?
    H: Name of the player, score
    Input: [CLS], what, is, ...,
    [SEP], name, of, the, player, [SEP], score,
    [SEP] sql, select, [SEP], sql, where, [SEP], sql, and, [SEP], ...

    Here, input is tokenized further by WordPiece (WP) tokenizer and fed into BERT.

    INPUT
    :param model_bert:
    :param tokenizer: WordPiece toknizer
    :param nlu: Question
    :param nlu_t: CoreNLP tokenized nlu.
    :param hds: Headers
    :param hs_t: None or 1st-level tokenized headers
    :param max_seq_length: max input token length

    OUTPUT
    tokens: BERT input tokens
    nlu_tt: WP-tokenized input natural language questions
    orig_to_tok_index: map the index of 1st-level-token to the index of 2nd-level-token
    tok_to_orig_index: inverse map.

    """

    l_n = []
    l_hs = []  # The length of columns for each batch
    l_input = []
    input_ids = []
    tokens = []
    segment_ids = []
    input_mask = []

    i_nlu = []  # index to retreive the position of contextual vector later.
    i_hds = []
    i_sql_vocab = []

    doc_tokens = []
    nlu_tt = []

    t_to_tt_idx = []
    tt_to_t_idx = []
    for b, nlu_t1 in enumerate(nlu_t):

        hds1 = hds[b]
        l_hs.append(len(hds1))

        # 1. 2nd tokenization using WordPiece
        tt_to_t_idx1 = []  # number indicates where sub-token belongs to in 1st-level-tokens (here, CoreNLP).
        t_to_tt_idx1 = []  # orig_to_tok_idx[i] = start index of i-th-1st-level-token in all_tokens.
        nlu_tt1 = []  # all_doc_tokens[ orig_to_tok_idx[i] ] returns first sub-token segement of i-th-1st-level-token
        for (i, token) in enumerate(nlu_t1):
            t_to_tt_idx1.append(
                len(nlu_tt1))  # all_doc_tokens[ indicate the start position of original 'white-space' tokens.
            sub_tokens = tokenizer.tokenize(token)
            for sub_token in sub_tokens:
                tt_to_t_idx1.append(i)
                nlu_tt1.append(sub_token)  # all_doc_tokens are further tokenized using WordPiece tokenizer
        nlu_tt.append(nlu_tt1)
        tt_to_t_idx.append(tt_to_t_idx1)
        t_to_tt_idx.append(t_to_tt_idx1)

        l_n.append(len(nlu_tt1))
        #         hds1_all_tok = tokenize_hds1(tokenizer, hds1)

        # [CLS] nlu [SEP] col1 [SEP] col2 [SEP] ...col-n [SEP]
        # 2. Generate BERT inputs & indices.
        # Combine hds1 and sql_vocab
        tokens1, segment_ids1, i_sql_vocab1, i_nlu1, i_hds1 = generate_inputs_s2s(tokenizer, nlu_tt1, hds1, sql_vocab)

        # i_hds1
        input_ids1 = tokenizer.convert_tokens_to_ids(tokens1)

        # Input masks
        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        input_mask1 = [1] * len(input_ids1)

        # 3. Zero-pad up to the sequence length.
        l_input.append(len(input_ids1))
        while len(input_ids1) < max_seq_length:
            input_ids1.append(0)
            input_mask1.append(0)
            segment_ids1.append(0)

        assert len(input_ids1) == max_seq_length
        assert len(input_mask1) == max_seq_length
        assert len(segment_ids1) == max_seq_length

        input_ids.append(input_ids1)
        tokens.append(tokens1)
        segment_ids.append(segment_ids1)
        input_mask.append(input_mask1)

        i_nlu.append(i_nlu1)
        i_hds.append(i_hds1)
        i_sql_vocab.append(i_sql_vocab1)

    # Convert to tensor
    all_input_ids = torch.tensor(input_ids, dtype=torch.long).to(device)
    all_input_mask = torch.tensor(input_mask, dtype=torch.long).to(device)
    all_segment_ids = torch.tensor(segment_ids, dtype=torch.long).to(device)

    # 4. Generate BERT output.
    all_encoder_layer, pooled_output = model_bert(all_input_ids, all_segment_ids, all_input_mask)

    # 5. generate l_hpu from i_hds
    l_hpu = gen_l_hpu(i_hds)

    return all_encoder_layer, pooled_output, tokens, i_nlu, i_hds, i_sql_vocab, \
           l_n, l_hpu, l_hs, l_input, \
           nlu_tt, t_to_tt_idx, tt_to_t_idx



def get_bert_output(model_bert, tokenizer, nlu_t, hds, max_seq_length):
    """
    Here, input is toknized further by WordPiece (WP) tokenizer and fed into BERT.

    INPUT
    :param model_bert:
    :param tokenizer: WordPiece toknizer
    :param nlu: Question
    :param nlu_t: CoreNLP tokenized nlu.
    :param hds: Headers
    :param hs_t: None or 1st-level tokenized headers
    :param max_seq_length: max input token length

    OUTPUT
    tokens: BERT input tokens
    nlu_tt: WP-tokenized input natural language questions
    orig_to_tok_index: map the index of 1st-level-token to the index of 2nd-level-token
    tok_to_orig_index: inverse map.

    """

    l_n = []
    l_hs = []  # The length of columns for each batch

    input_ids = []
    tokens = []
    segment_ids = []
    input_mask = []

    i_nlu = []  # index to retreive the position of contextual vector later.
    i_hds = []

    doc_tokens = []
    nlu_tt = []

    t_to_tt_idx = []
    tt_to_t_idx = []
    # print('nlu_t', nlu_t)
    for b, nlu_t1 in enumerate(nlu_t):

        hds1 = deepcopy(hds[b])
        hds1.append("空列")
        l_hs.append(len(hds1))

        # print('hds1:', hds1)
        # print('nlu t1:', len(nlu_t1), nlu_t1)

        # 1. 2nd tokenization using WordPiece
        # tt_to_t_idx1 = []  # number indicates where sub-token belongs to in 1st-level-tokens (here, CoreNLP).
        # t_to_tt_idx1 = []  # orig_to_tok_idx[i] = start index of i-th-1st-level-token in all_tokens.
        # nlu_tt1 = []  # all_doc_tokens[ orig_to_tok_idx[i] ] returns first sub-token segement of i-th-1st-level-token
        # for (i, token) in enumerate(nlu_t1):
        #     t_to_tt_idx1.append(
        #         len(nlu_tt1))  # all_doc_tokens[ indicate the start position of original 'white-space' tokens.
        #     sub_tokens = tokenizer.tokenize(token)
        #     for sub_token in sub_tokens:
        #         tt_to_t_idx1.append(i)
        #         nlu_tt1.append(sub_token)  # all_doc_tokens are further tokenized using WordPiece tokenizer
        # nlu_tt.append(nlu_tt1)
        # tt_to_t_idx.append(tt_to_t_idx1)
        # t_to_tt_idx.append(t_to_tt_idx1)
        # print('nlu ti:', len(nlu_t1), nlu_t1)

        l_n.append(len(nlu_t1))
        #         hds1_all_tok = tokenize_hds1(tokenizer, hds1)

        # [CLS] nlu [SEP] col1 [SEP] col2 [SEP] ...col-n [SEP]
        # 2. Generate BERT inputs & indices.
        tokens1, segment_ids1, i_nlu1, i_hds1 = generate_inputs(tokenizer, nlu_t1, hds1)
        input_ids1 = tokenizer.convert_tokens_to_ids(tokens1)

        # print('tokens1:', tokens1)
        # print('input ids:', input_ids1)
        # print('segmentids:', segment_ids1)

        # Input masks
        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        input_mask1 = [1] * len(input_ids1)

        # 3. Zero-pad up to the sequence length.

        while len(input_ids1) < max_seq_length:
            input_ids1.append(0)
            input_mask1.append(0)
            segment_ids1.append(0)

        if len(input_ids1)!=max_seq_length:
            print("Error: ", nlu_t1, tokens1, len(input_ids1), max_seq_length)

        assert len(input_ids1) == max_seq_length
        assert len(input_mask1) == max_seq_length
        assert len(segment_ids1) == max_seq_length

        input_ids.append(input_ids1)
        tokens.append(tokens1)
        segment_ids.append(segment_ids1)
        input_mask.append(input_mask1)

        i_nlu.append(i_nlu1)
        i_hds.append(i_hds1)

    # Convert to tensor
    all_input_ids = torch.tensor(input_ids, dtype=torch.long).to(device)
    all_input_mask = torch.tensor(input_mask, dtype=torch.long).to(device)
    all_segment_ids = torch.tensor(segment_ids, dtype=torch.long).to(device)

    # 4. Generate BERT output.
    # print('all input:', all_input_ids)
    all_encoder_layer, pooled_output = model_bert(all_input_ids, all_segment_ids)

    # 5. generate l_hpu from i_hds
    # print('all', all_encoder_layer.shape)
    # print(' poold', pooled_output.shape)
    # print('inlu:', i_nlu)
    # print('ihds:', i_hds)


    l_hpu = gen_l_hpu(i_hds)
    # print('l hpu:', l_hpu)

    return all_encoder_layer, pooled_output, tokens, i_nlu, i_hds, \
           l_n, l_hpu, l_hs


def get_wemb_n(i_nlu, l_n, hS, num_hidden_layers, all_encoder_layer, num_out_layers_n):
    """
    Get the representation of each tokens.
    """
    # print('\n\nget emb nlu:')
    # print('i nlu:', i_nlu)
    # print('l n:', l_n)
    # print('all encoder layer:', all_encoder_layer.shape)

    bS = len(l_n)
    l_n_max = max(l_n)
    wemb_n = torch.zeros([bS, l_n_max, hS * num_out_layers_n]).to(device)
    for b in range(bS):
        # [B, max_len, dim]
        # Fill zero for non-exist part.
        l_n1 = l_n[b]
        i_nlu1 = i_nlu[b]
        for i_noln in range(num_out_layers_n):
            i_layer = num_hidden_layers - 1 - i_noln
            st = i_noln * hS
            ed = (i_noln + 1) * hS
            wemb_n[b, 0:(i_nlu1[1] - i_nlu1[0]), st:ed] = all_encoder_layer[i_layer][b, i_nlu1[0]:i_nlu1[1], :]
    return wemb_n
    #


def get_wemb_h(i_hds, l_hpu, l_hs, hS, num_hidden_layers, all_encoder_layer, num_out_layers_h):
    """
    As if
    [ [table-1-col-1-tok1, t1-c1-t2, ...],
       [t1-c2-t1, t1-c2-t2, ...].
       ...
       [t2-c1-t1, ...,]
    ]
    """
    # print('\n\nget emb hds:')
    # print('ihds:', i_hds)
    # print('l_hpu:', l_hpu)
    # print('l_hs:', l_hs)
    # print('all encoder layer:', all_encoder_layer.shape)
    # print('***\n\n')


    bS = len(l_hs)
    l_hpu_max = max(l_hpu)
    num_of_all_hds = sum(l_hs)
    wemb_h = torch.zeros([num_of_all_hds, l_hpu_max, hS * num_out_layers_h]).to(device)
    b_pu = -1
    for b, i_hds1 in enumerate(i_hds):
        for b1, i_hds11 in enumerate(i_hds1):
            b_pu += 1
            for i_nolh in range(num_out_layers_h):
                i_layer = num_hidden_layers - 1 - i_nolh
                st = i_nolh * hS
                ed = (i_nolh + 1) * hS
                wemb_h[b_pu, 0:(i_hds11[1] - i_hds11[0]), st:ed] \
                    = all_encoder_layer[i_layer][b, i_hds11[0]:i_hds11[1], :]

    return wemb_h


def get_wemb_bert(bert_config, model_bert, tokenizer, nlu_t, hds, max_seq_length, num_out_layers_n=1,
                  num_out_layers_h=1):
    # print('nlu_t:', nlu_t)
    # print('hds:', hds)
    # get contextual output of all tokens from bert
    all_encoder_layer, pooled_output, tokens, i_nlu, i_hds, \
    l_n, l_hpu, l_hs = get_bert_output(model_bert, tokenizer, nlu_t, hds, max_seq_length)
    # all_encoder_layer: BERT outputs from all layers.
    # pooled_output: output of [CLS] vec.
    # tokens: BERT intput tokens
    # i_nlu: start and end indices of question in tokens
    # i_hds: start and end indices of headers
    # get the wemb
    # print('pooled:', pooled_output.shape)
    wemb_n = get_wemb_n(i_nlu, l_n, bert_config.hidden_size, bert_config.num_hidden_layers, all_encoder_layer,
                        num_out_layers_n)

    wemb_h = get_wemb_h(i_hds, l_hpu, l_hs, bert_config.hidden_size, bert_config.num_hidden_layers, all_encoder_layer,
                        num_out_layers_h)

    return wemb_n, wemb_h, l_n, l_hpu, l_hs


def gen_pnt_n(g_wvi, mL_w, mL_nt):
    """
    Generate one-hot idx indicating vectors with their lenghts.

    :param g_wvi: e.g. [[[0, 6, 7, 8, 15], [0, 1, 2, 3, 4, 15]], [[0, 1, 2, 3, 16], [0, 7, 8, 9, 16]]]
    where_val idx in nlu_t. 0 = <BEG>, -1 = <END>.
    :param mL_w: 4
    :param mL_nt: 200
    :return:
    """
    bS = len(g_wvi)
    for g_wvi1 in g_wvi:
        for g_wvi11 in g_wvi1:
            l11 = len(g_wvi11)

    mL_g_wvi = max([max([0] + [len(tok) for tok in gwsi]) for gwsi in g_wvi]) - 1
    # zero because of '' case.
    # -1 because we already have <BEG>
    if mL_g_wvi < 1:
        mL_g_wvi = 1
    # NLq_token_pos = torch.zeros(bS, 5 - 1, mL_g_wvi, self.max_NLq_token_num)

    # l_g_wvi = torch.zeros(bS, 5 - 1)
    pnt_n = torch.zeros(bS, mL_w, mL_g_wvi, mL_nt).to(device)  # one hot
    l_g_wvi = torch.zeros(bS, mL_w).to(device)

    for b, g_wvi1 in enumerate(g_wvi):
        i_wn = 0  # To prevent error from zero number of condition.
        for i_wn, g_wvi11 in enumerate(g_wvi1):
            # g_wvi11: [0, where_conds pos in NLq, end]
            g_wvi11_n1 = g_wvi11[:-1]  # doesn't count <END> idx.
            l_g_wvi[b, i_wn] = len(g_wvi11_n1)
            for t, idx in enumerate(g_wvi11_n1):
                pnt_n[b, i_wn, t, idx] = 1

            # Pad
        if i_wn < (mL_w - 1):  # maximum number of conidtions is 4
            pnt_n[b, i_wn + 1:, 0, 1] = 1  # # cannot understand... [<BEG>, <END>]??
            l_g_wvi[b, i_wn + 1:] = 1  # it means there is only <BEG>.

    return pnt_n, l_g_wvi


def pred_sc(s_sc):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    """
    # get g_num
    pr_sc = []
    for s_sc1 in s_sc:
        pr_sc.append(s_sc1.argmax().item())

    return pr_sc


def pred_sc_beam(s_sc, beam_size):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    """
    # get g_num
    pr_sc_beam = []

    for s_sc1 in s_sc:
        val, idxes = s_sc1.topk(k=beam_size)
        pr_sc_beam.append(idxes.tolist())

    return pr_sc_beam


def pred_sa(s_sa):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    """
    # get g_num
    pr_sa = []
    for s_sa1 in s_sa:
        pr_sa.append(s_sa1.argmax().item())

    return pr_sa


def pred_scco(s_cco, wn):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    """
    # get g_num
    pr_scco = []
    for b, s_cco1 in enumerate(s_cco):
        # if where num is 1, cco must be 0
        if wn[b] == 1:
            pr_scco.append(s_cco1[0].argmax().item())
        # if where num > 1, cco must be 1 or 2
        else:
            pr_scco.append(s_cco1[1:].argmax().item() + 1)

    return pr_scco


def pred_scco_value(s_cco, wn):
    pr_scco = []
    pr_scco_value = []
    for b, s_cco1 in enumerate(s_cco):
        if wn[b] == 1:
            pr_scco.append(s_cco1[0].argmax().item())
        else:
            pr_scco.append(s_cco1[1:].argmax().item() + 1)
        pr_scco_value.append(get_tensor_value(F.softmax(s_cco1, dim=0), [pr_scco[-1]]))

    return pr_scco, pr_scco_value


def pred_wn(s_wn):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    """
    # get g_num
    pr_wn = []
    for s_wn1 in s_wn:
        pr_wn.append(s_wn1.argmax().item())
        # print(pr_wn, s_wn1)
        # if s_wn1.argmax().item() == 3:
        #     input('')

    return pr_wn


def pred_wn_value(s_wn):
    pr_wn = []
    pr_wn_value = []
    for s_wn1 in s_wn:
        pr_wn.append(s_wn1.argmax().item())
        pr_wn_value.append(get_tensor_value(F.softmax(s_wn1, dim=0), [pr_wn[-1]]))
    
    return pr_wn, pr_wn_value


def pred_slen(s_slen):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    """
    # get g_num
    pr_slen = []
    for s_slen1 in s_slen:
        pr_slen.append(s_slen1.argmax().item())
        # print(pr_wn, s_wn1)
        # if s_wn1.argmax().item() == 3:
        #     input('')

    return pr_slen

def pred_slen_value(s_slen):
    pr_slen = []
    pr_slen_value = []
    for s_slen1 in s_slen:
        pr_slen.append(s_slen1.argmax().item())
        #pr_slen_value.append(F.softmax(s_slen1, dim=0).max().item())
        pr_slen_value.append(get_tensor_value(F.softmax(s_slen1, dim=0), [pr_slen[-1]]))

    return pr_slen, pr_slen_value
        

def pred_wc_old(sql_i, s_wc):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    """
    # get g_num
    pr_wc = []
    for b, sql_i1 in enumerate(sql_i):
        wn = len(sql_i1['conds'])
        s_wc1 = s_wc[b]

        pr_wc1 = argsort(-s_wc1.data.cpu().numpy())[:wn]
        pr_wc1.sort()

        pr_wc.append(list(pr_wc1))
    return pr_wc


def pred_wc(wn, s_wc):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    ! Returned index is sorted!
    """
    # get g_num
    pr_wc = []
    for b, wn1 in enumerate(wn):
        s_wc1 = s_wc[b]  # [hs, 4]
        # print(s_wc1.shape, wn1)
        # print(s_wc1.data.cpu().numpy)
        # print(np.argmax(s_wc1.data.cpu().numpy(), axis=0))
        pr_wc1 = np.argmax(s_wc1.data.cpu().numpy(), axis=0)[:wn1]
        # pr_wc1 = argsort(-s_wc1.data.cpu().numpy())[:wn1]
        pr_wc1.sort()

        pr_wc.append(list(pr_wc1))
    return pr_wc

def pred_wc_value(wn, s_wc):
    pr_wc = []
    pr_wc_value = []
    for b, wn1 in enumerate(wn):
        s_wc1 = s_wc[b]  # [hs, 4]
        s_wc1_t = torch.transpose(s_wc1, 1, 0)
        pr_wc1 = np.argmax(s_wc1.data.cpu().numpy(), axis=0)[:wn1]
        pr_wc1.sort()
        pr_wc.append(list(pr_wc1))
        values = []
        for j, pr_wc11 in enumerate(list(pr_wc1)):
            sf_value = F.softmax(s_wc1_t[j], dim=0)
            pr_wc_value1 = get_tensor_value(sf_value, [pr_wc11])
            values.append(pr_wc_value1[0])
        pr_wc_value.append(values)
    return pr_wc, pr_wc_value


def pred_sc_multi(slen, s_sc):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    ! Returned index is sorted!
    """
    # get g_num
    pr_sc = []
    for b, slen1 in enumerate(slen):
        s_sc1 = s_sc[b]

        pr_sc1 = argsort(-s_sc1.data.cpu().numpy())[:slen1]
        pr_sc1.sort()
        # idx = np.sort(pr_sc1)

        pr_sc.append(list(pr_sc1))
    return pr_sc


def pred_sc_multi_value(slen, s_sc):
    pr_sc = []
    pr_sc_value = []
    for b, slen1 in enumerate(slen):
        s_sc1 = s_sc[b]

        pr_sc1 = argsort(-s_sc1.data.cpu().numpy())[:slen1]
        pr_sc1.sort()
        pr_sc.append(list(pr_sc1))

        sf_value = F.softmax(s_sc1, dim=0)
        #print("sf_value: ", sf_value)
        pr_sc_value1 = get_tensor_value(sf_value, list(pr_sc1))
        pr_sc_value.append(pr_sc_value1)
    return pr_sc, pr_sc_value


def get_tensor_value(values, indexs):
    weights = []
    for index in indexs:
        weights.append(round(values[index].item(), 3))
    return weights


def pred_sa_multi(wn, s_wo):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    ! Returned index is sorted!
    """
    # get g_num

    pr_wo_a = s_wo.argmax(dim=2)  # [B, 4]
    # get g_num
    pr_wo = []
    for b, pr_wo_a1 in enumerate(pr_wo_a):
        wn1 = wn[b]
        pr_wo.append(list(pr_wo_a1.data.cpu().numpy()[:wn1]))

    return pr_wo


def pred_sa_multi_value(wn, s_wo):
    pr_wo_a = s_wo.argmax(dim=2)  # [B, 4]
    pr_wo = []
    pr_wo_value = []
    for b, pr_wo_a1 in enumerate(pr_wo_a):
        wn1 = wn[b]
        pr_wo1 = pr_wo_a1.data.cpu().numpy()[:wn1]
        pr_wo.append(list(pr_wo1))

        s_wo1 = s_wo[b]
        values = []
        for j, pr_wo11 in enumerate(list(pr_wo1)):
            sf_value = F.softmax(s_wo1[j], dim=0)
            pr_wo_value1 = get_tensor_value(sf_value, [pr_wo11])
            values.append(pr_wo_value1[0])
        pr_wo_value.append(values)
    return pr_wo, pr_wo_value


def pred_wc_sorted_by_prob(s_wc):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    ! Returned index is sorted by prob.
    All colume-indexes are returned here.
    """
    # get g_num
    bS = len(s_wc)
    pr_wc = []

    for b in range(bS):
        s_wc1 = s_wc[b]
        pr_wc1 = argsort(-s_wc1.data.cpu().numpy())
        pr_wc.append(list(pr_wc1))
    return pr_wc


def pred_wo(wn, s_wo):
    """
    return: [ pr_wc1_i, pr_wc2_i, ...]
    """
    # s_wo = [B, 4, n_op]
    pr_wo_a = s_wo.argmax(dim=2)  # [B, 4]
    # get g_num
    pr_wo = []
    for b, pr_wo_a1 in enumerate(pr_wo_a):
        wn1 = wn[b]
        pr_wo.append(list(pr_wo_a1.data.cpu().numpy()[:wn1]))

    return pr_wo


def pred_wo_value(wn, s_wo):
    pr_wo_a = s_wo.argmax(dim=2)  # [B, 4]
    pr_wo = []
    pr_wo_value = []
    for b, pr_wo_a1 in enumerate(pr_wo_a):
        wn1 = wn[b]
        pr_wo1 = pr_wo_a1.data.cpu().numpy()[:wn1]
        pr_wo.append(list(pr_wo1))

        s_wo1 = s_wo[b]
        values = []
        for j, pr_wo11 in enumerate(list(pr_wo1)):
            sf_value = F.softmax(s_wo1[j], dim=0)
            pr_wo_value1 = get_tensor_value(sf_value, [pr_wo11])
            values.append(pr_wo_value1[0])
        pr_wo_value.append(values)

    return pr_wo, pr_wo_value



def pred_wvi_se(wn, s_wv):
    """
    s_wv: [B, 4, mL, 2]
    - predict best st-idx & ed-idx
    """

    s_wv_st, s_wv_ed = s_wv.split(1, dim=3)  # [B, 4, mL, 2] -> [B, 4, mL, 1], [B, 4, mL, 1]

    s_wv_st = s_wv_st.squeeze(3)  # [B, 4, mL, 1] -> [B, 4, mL]
    s_wv_ed = s_wv_ed.squeeze(3)

    pr_wvi_st_idx = s_wv_st.argmax(dim=2)  # [B, 4, mL] -> [B, 4, 1]
    # pr_wvi_ed_idx = s_wv_ed.argmax(dim=2)

    pr_wvi = []
    for b, wn1 in enumerate(wn):
        pr_wvi1 = []
        for i_wn in range(wn1):
            pr_wvi_st_idx11 = pr_wvi_st_idx[b][i_wn]
            pr_wvi_ed_idx11 = s_wv_ed[b][i_wn][pr_wvi_st_idx11:].argmax() + pr_wvi_st_idx11
            pr_wvi1.append([pr_wvi_st_idx11.item(), pr_wvi_ed_idx11.item()])
        pr_wvi.append(pr_wvi1)

    return pr_wvi


def pred_wvi_se_value(wn, s_wv):
    s_wv_st, s_wv_ed = s_wv.split(1, dim=3)  # [B, 4, mL, 2] -> [B, 4, mL, 1], [B, 4, mL, 1]
    s_wv_st = s_wv_st.squeeze(3)  # [B, 4, mL, 1] -> [B, 4, mL]
    s_wv_ed = s_wv_ed.squeeze(3)

    pr_wvi_st_idx = s_wv_st.argmax(dim=2)  # [B, 4, mL] -> [B, 4, 1]
    pr_wvi = []
    pr_wvi_value = []
    for b, wn1 in enumerate(wn):
        pr_wvi1 = []
        pr_wvi_value1 = []
        for i_wn in range(wn1):
            pr_wvi_st_idx11 = pr_wvi_st_idx[b][i_wn]
            pr_wvi_ed_idx11 = s_wv_ed[b][i_wn][pr_wvi_st_idx11:].argmax() + pr_wvi_st_idx11
            pr_wvi1.append([pr_wvi_st_idx11.item(), pr_wvi_ed_idx11.item()])

            sf_st_value = F.softmax(s_wv_st[b, i_wn], dim=0)
            pr_st_value1 = get_tensor_value(sf_st_value, [pr_wvi_st_idx11.item()])
            sf_ed_value = F.softmax(s_wv_ed[b, i_wn], dim=0)
            pr_ed_value1 = get_tensor_value(sf_ed_value, [pr_wvi_ed_idx11.item()])
            pr_wvi_value1.append([pr_st_value1[0], pr_ed_value1[0]])
        pr_wvi.append(pr_wvi1)
        pr_wvi_value.append(pr_wvi_value1)

    return pr_wvi, pr_wvi_value


def pred_wvi_se_beam(max_wn, s_wv, beam_size):
    """
    s_wv: [B, 4, mL, 2]
    - predict best st-idx & ed-idx


    output:
    pr_wvi_beam = [B, max_wn, n_pairs, 2]. 2 means [st, ed].
    prob_wvi_beam = [B, max_wn, n_pairs]
    """
    bS = s_wv.shape[0]

    s_wv_st, s_wv_ed = s_wv.split(1, dim=3)  # [B, 4, mL, 2] -> [B, 4, mL, 1], [B, 4, mL, 1]

    s_wv_st = s_wv_st.squeeze(3)  # [B, 4, mL, 1] -> [B, 4, mL]
    s_wv_ed = s_wv_ed.squeeze(3)

    prob_wv_st = F.softmax(s_wv_st, dim=-1).detach().to('cpu').numpy()
    prob_wv_ed = F.softmax(s_wv_ed, dim=-1).detach().to('cpu').numpy()

    k_logit = int(ceil(sqrt(beam_size)))
    n_pairs = k_logit ** 2
    assert n_pairs >= beam_size
    values_st, idxs_st = s_wv_st.topk(k_logit)  # [B, 4, mL] -> [B, 4, k_logit]
    values_ed, idxs_ed = s_wv_ed.topk(k_logit)  # [B, 4, mL] -> [B, 4, k_logit]

    # idxs = [B, k_logit, 2]
    # Generate all possible combination of st, ed indices & prob
    pr_wvi_beam = []  # [B, max_wn, k_logit**2 [st, ed] paris]
    prob_wvi_beam = zeros([bS, max_wn, n_pairs])
    for b in range(bS):
        pr_wvi_beam1 = []

        idxs_st1 = idxs_st[b]
        idxs_ed1 = idxs_ed[b]
        for i_wn in range(max_wn):
            idxs_st11 = idxs_st1[i_wn]
            idxs_ed11 = idxs_ed1[i_wn]

            pr_wvi_beam11 = []
            pair_idx = -1
            for i_k in range(k_logit):
                for j_k in range(k_logit):
                    pair_idx += 1
                    st = idxs_st11[i_k].item()
                    ed = idxs_ed11[j_k].item()
                    pr_wvi_beam11.append([st, ed])

                    p1 = prob_wv_st[b, i_wn, st]
                    p2 = prob_wv_ed[b, i_wn, ed]
                    prob_wvi_beam[b, i_wn, pair_idx] = p1 * p2
            pr_wvi_beam1.append(pr_wvi_beam11)
        pr_wvi_beam.append(pr_wvi_beam1)

    # prob

    return pr_wvi_beam, prob_wvi_beam


def is_whitespace_g_wvi(c):
    # if c == " " or c == "\t" or c == "\r" or c == "\n" or ord(c) == 0x202F:
    if c == " ":
        return True
    return False


def convert_pr_wvi_to_string(pr_wvi, nlu_t, nlu):
    """
    - Convert to the string in whilte-space-separated tokens
    - Add-hoc addition.
    """
    pr_wv_str_wp = []  # word-piece version
    pr_wv_str = []
    for b, pr_wvi1 in enumerate(pr_wvi):
        pr_wv_str_wp1 = []
        pr_wv_str1 = []
        nlu_t1 = nlu_t[b]

        for i_wn, pr_wvi11 in enumerate(pr_wvi1):
            st_idx, ed_idx = pr_wvi11

            # Ad-hoc modification of ed_idx to deal with wp-tokenization effect.
            # e.g.) to convert "butler cc (" ->"butler cc (ks)" (dev set 1st question).
            pr_wv_str_wp11 = nlu_t1[st_idx:ed_idx + 1]
            pr_wv_str_wp1.append(pr_wv_str_wp11)

            while ed_idx + 1 < len(nlu_t1) and nlu_t1[ed_idx + 1].startswith('##'):
                ed_idx += 1
            pr_wv_str11 = nlu_t1[st_idx:ed_idx + 1]
            # print(st_wh_idx, ed_wh_idx)

            pr_wv_str1.append(pr_wv_str11)

        pr_wv_str_wp.append(pr_wv_str_wp1)
        pr_wv_str.append(pr_wv_str1)

    return pr_wv_str, pr_wv_str_wp


def pred_sw_se(s_sc, s_cco, s_sa, s_wn, s_wc, s_wo, s_wv, s_slen):
    #pr_slen = pred_slen(s_slen)
    pr_slen, pr_slen_value = pred_slen_value(s_slen)
    #print("sxron pr_slen: ", pr_slen)
    #print("sxron pr_slen_value: ", pr_slen_value)
    #pr_sc = pred_sc_multi(pr_slen, s_sc)
    pr_sc, pr_sc_value = pred_sc_multi_value(pr_slen, s_sc)
    #print("sxron pr_sc: ", pr_sc)
    #print("sxron pr_sc_value: ", pr_sc_value)

    #pr_sa = pred_sa_multi(pr_slen, s_sa)
    pr_sa, pr_sa_value = pred_sa_multi_value(pr_slen, s_sa)
    #print("sxron pr_sa: ", pr_sa)
    #print("sxron pr_sa_value: ", pr_sa_value)

    #pr_wn = pred_wn(s_wn)
    pr_wn, pr_wn_value = pred_wn_value(s_wn)
    #print("sxron pr_wn: ", pr_wn)
    #print("sxron pr_wn_value: ", pr_wn_value)

    #pr_scco = pred_scco(s_cco, pr_wn)
    pr_scco, pr_scco_value = pred_scco_value(s_cco, pr_wn)
    #print("sxron pr_scco: ", pr_scco)
    #print("sxron pr_scco_value: ", pr_scco_value)

    #pr_wc = pred_wc(pr_wn, s_wc)
    pr_wc, pr_wc_value = pred_wc_value(pr_wn, s_wc)
    #print("sxron pr_wc: ", pr_wc)
    #print("sxron pr_wc_value: ", pr_wc_value)

    #pr_wo = pred_wo(pr_wn, s_wo)
    pr_wo, pr_wo_value = pred_wo_value(pr_wn, s_wo)
    #print("sxron pr_wo: ", pr_wo)
    #print("sxron pr_wo_value: ", pr_wo_value)

    #pr_wvi = pred_wvi_se(pr_wn, s_wv)
    pr_wvi, pr_wvi_value = pred_wvi_se_value(pr_wn, s_wv)
    #print("sxron pr_wvi: ", pr_wvi)
    #print("sxron pr_wvi_value: ", pr_wvi_value)

    return pr_sc, pr_scco, pr_sa, pr_wn, pr_wc, pr_wo, pr_wvi, pr_slen


def merge_wv_t1_eng(where_str_tokens, NLq):
    """
    Almost copied of SQLNet.
    The main purpose is pad blank line while combining tokens.
    """
    nlq = NLq.lower()
    where_str_tokens = [tok.lower() for tok in where_str_tokens]
    alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789$'
    special = {'-LRB-': '(',
               '-RRB-': ')',
               '-LSB-': '[',
               '-RSB-': ']',
               '``': '"',
               '\'\'': '"',
               }
    # '--': '\u2013'} # this generate error for test 5661 case.
    ret = ''
    double_quote_appear = 0
    for raw_w_token in where_str_tokens:
        # if '' (empty string) of None, continue
        if not raw_w_token:
            continue

        # Change the special characters
        w_token = special.get(raw_w_token, raw_w_token)  # maybe necessary for some case?

        # check the double quote
        if w_token == '"':
            double_quote_appear = 1 - double_quote_appear

        # Check whether ret is empty. ret is selected where condition.
        if len(ret) == 0:
            pass
        # Check blank character.
        elif len(ret) > 0 and ret + ' ' + w_token in nlq:
            # Pad ' ' if ret + ' ' is part of nlq.
            ret = ret + ' '

        elif len(ret) > 0 and ret + w_token in nlq:
            pass  # already in good form. Later, ret + w_token will performed.

        # Below for unnatural question I guess. Is it likely to appear?
        elif w_token == '"':
            if double_quote_appear:
                ret = ret + ' '  # pad blank line between next token when " because in this case, it is of closing apperas
                # for the case of opening, no blank line.

        elif w_token[0] not in alphabet:
            pass  # non alphabet one does not pad blank line.

        # when previous character is the special case.
        elif (ret[-1] not in ['(', '/', '\u2013', '#', '$', '&']) and (ret[-1] != '"' or not double_quote_appear):
            ret = ret + ' '
        ret = ret + w_token

    return ret.strip()


def find_sql_where_op(gt_sql_tokens_part):
    """
    gt_sql_tokens_part: Between 'WHERE' and 'AND'(if exists).
    """
    # sql_where_op = ['=', 'EQL', '<', 'LT', '>', 'GT']
    sql_where_op = ['EQL', 'LT', 'GT']  # wv sometimes contains =, < or >.

    for sql_where_op in sql_where_op:
        if sql_where_op in gt_sql_tokens_part:
            found_sql_where_op = sql_where_op
            break

    return found_sql_where_op


def find_sub_list(sl, l):
    # from stack overflow.
    results = []
    sll = len(sl)
    for ind in (i for i, e in enumerate(l) if e == sl[0]):
        if l[ind:ind + sll] == sl:
            results.append((ind, ind + sll - 1))

    return results


def get_g_wvi_bert(nlu, nlu_t, wh_to_wp_index, sql_i, sql_t, tokenizer, nlu_wp_t):
    """
    Generate SQuAD style start and end index of wv in nlu. Index is for of after WordPiece tokenization.

    Assumption: where_str always presents in the nlu.
    """
    g_wvi = []
    for b, sql_i1 in enumerate(sql_i):
        nlu1 = nlu[b]
        nlu_t1 = nlu_t[b]
        nlu_wp_t1 = nlu_wp_t[b]
        sql_t1 = sql_t[b]
        wh_to_wp_index1 = wh_to_wp_index[b]

        st = sql_t1.index('WHERE') + 1 if 'WHERE' in sql_t1 else len(sql_t1)
        g_wvi1 = []
        while st < len(sql_t1):
            if 'AND' not in sql_t1[st:]:
                ed = len(sql_t1)
            else:
                ed = sql_t1[st:].index('AND') + st
            sql_wop = find_sql_where_op(sql_t1[st:ed])  # sql where operator
            st_wop = st + sql_t1[st:ed].index(sql_wop)

            wv_str11_t = sql_t1[st_wop + 1:ed]
            results = find_sub_list(wv_str11_t, nlu_t1)
            st_idx, ed_idx = results[0]

            st_wp_idx = wh_to_wp_index1[st_idx]
            ed_wp_idx = wh_to_wp_index1[ed_idx]

            g_wvi11 = [st_wp_idx, ed_wp_idx]
            g_wvi1.append(g_wvi11)
            st = ed + 1
        g_wvi.append(g_wvi1)

    return g_wvi


def get_amr_infos(t, l_n, l_hs):
    batch_size = len(l_n)
    maxlen = 0
    for i, ln in enumerate(l_n):
        if ln+ l_hs[i] > maxlen: maxlen = ln+ l_hs[i]
    part_masks = Variable(torch.Tensor(batch_size, maxlen).zero_(), requires_grad=False)
    
    heads = []
    deps = []
    # print('ln:',l_n)
    for b, t1 in enumerate(t):
        # print('s ques:', len(t1['struct_question']), t1['struct_question'])
        assert len(t1['struct_question']) == len(t1['struct_label'])
        assert len(t1['struct_question']) == l_n[b]
        head = np.zeros((l_n[b] + l_hs[b]), dtype=np.int32)
        dep = np.zeros((l_n[b] + l_hs[b]), dtype=np.int32)
        # print('headi:', head.size)
        
        for j in range(l_n[b]):
            head[j] = t1['struct_question'][j] + l_n[b]
            dep[j] = t1['struct_label'][j]
            part_masks[b, j] = 1

        heads.append(head)
        deps.append(dep)

    return heads, deps, part_masks


def get_g_wvi_bert_from_g_wvi_corenlp(wh_to_wp_index, g_wvi_corenlp):
    """
    Generate SQuAD style start and end index of wv in nlu. Index is for of after WordPiece tokenization.

    Assumption: where_str always presents in the nlu.
    """
    g_wvi = []
    for b, g_wvi_corenlp1 in enumerate(g_wvi_corenlp):
        wh_to_wp_index1 = wh_to_wp_index[b]
        g_wvi1 = []
        for i_wn, g_wvi_corenlp11 in enumerate(g_wvi_corenlp1):
            st_idx, ed_idx = g_wvi_corenlp11

            if st_idx == -100 and ed_idx == -100:
                st_wp_idx = -100
                ed_wp_idx = -100
            else:
                st_wp_idx = wh_to_wp_index1[st_idx]
                ed_wp_idx = wh_to_wp_index1[ed_idx]

            g_wvi11 = [st_wp_idx, ed_wp_idx]
            g_wvi1.append(g_wvi11)

        g_wvi.append(g_wvi1)

    return g_wvi


def get_g_wvi_bert_from_sql_i(nlu, nlu_t, wh_to_wp_index, sql_i, sql_t, tokenizer, nlu_wp_t):
    """
    Generate SQuAD style start and end index of wv in nlu. Index is for of after WordPiece tokenization.

    Assumption: where_str always presents in the nlu.
    """
    g_wvi = []
    for b, sql_i1 in enumerate(sql_i):
        nlu1 = nlu[b]
        nlu_t1 = nlu_t[b]
        nlu_wp_t1 = nlu_wp_t[b]
        sql_t1 = sql_t[b]
        wh_to_wp_index1 = wh_to_wp_index[b]

        st = sql_t1.index('WHERE') + 1 if 'WHERE' in sql_t1 else len(sql_t1)
        g_wvi1 = []
        while st < len(sql_t1):
            if 'AND' not in sql_t1[st:]:
                ed = len(sql_t1)
            else:
                ed = sql_t1[st:].index('AND') + st
            sql_wop = find_sql_where_op(sql_t1[st:ed])  # sql where operator
            st_wop = st + sql_t1[st:ed].index(sql_wop)

            wv_str11_t = sql_t1[st_wop + 1:ed]
            results = find_sub_list(wv_str11_t, nlu_t1)
            st_idx, ed_idx = results[0]

            st_wp_idx = wh_to_wp_index1[st_idx]
            ed_wp_idx = wh_to_wp_index1[ed_idx]

            g_wvi11 = [st_wp_idx, ed_wp_idx]
            g_wvi1.append(g_wvi11)
            st = ed + 1
        g_wvi.append(g_wvi1)

    return g_wvi


def get_cnt_sc(g_sc, pr_sc):
    cnt = 0
    for b, g_sc1 in enumerate(g_sc):
        pr_sc1 = pr_sc[b]
        if pr_sc1 == g_sc1:
            cnt += 1

    return cnt


def get_cnt_sc_list(g_sc, pr_sc):
    cnt_list = []
    for b, g_sc1 in enumerate(g_sc):
        pr_sc1 = pr_sc[b]
        if pr_sc1 == g_sc1:
            cnt_list.append(1)
        else:
            cnt_list.append(0)

    return cnt_list


def get_cnt_sa(g_sa, pr_sa):
    cnt = 0
    for b, g_sa1 in enumerate(g_sa):
        pr_sa1 = pr_sa[b]
        if pr_sa1 == g_sa1:
            cnt += 1

    return cnt


def get_cnt_wn(g_wn, pr_wn):
    cnt = 0
    for b, g_wn1 in enumerate(g_wn):
        pr_wn1 = pr_wn[b]
        if pr_wn1 == g_wn1:
            cnt += 1

    return cnt


def get_cnt_wc(g_wc, pr_wc):
    cnt = 0
    for b, g_wc1 in enumerate(g_wc):

        pr_wc1 = pr_wc[b]
        pr_wn1 = len(pr_wc1)
        g_wn1 = len(g_wc1)

        if pr_wn1 != g_wn1:
            continue
        else:
            wc1 = array(g_wc1)
            wc1.sort()

            if array_equal(pr_wc1, wc1):
                cnt += 1

    return cnt


def get_cnt_wc_list(g_wc, pr_wc):
    cnt_list = []
    for b, g_wc1 in enumerate(g_wc):

        pr_wc1 = pr_wc[b]
        pr_wn1 = len(pr_wc1)
        g_wn1 = len(g_wc1)

        if pr_wn1 != g_wn1:
            cnt_list.append(0)
            continue
        else:
            wc1 = array(g_wc1)
            wc1.sort()

            if array_equal(pr_wc1, wc1):
                cnt_list.append(1)
            else:
                cnt_list.append(0)

    return cnt_list


def get_cnt_wo(g_wn, g_wc, g_wo, pr_wc, pr_wo, mode):
    """ pr's are all sorted as pr_wc are sorted in increasing order (in column idx)
        However, g's are not sorted.

        Sort g's in increasing order (in column idx)
    """
    cnt = 0
    for b, g_wo1 in enumerate(g_wo):
        g_wc1 = g_wc[b]
        pr_wc1 = pr_wc[b]
        pr_wo1 = pr_wo[b]
        pr_wn1 = len(pr_wo1)
        g_wn1 = g_wn[b]

        if g_wn1 != pr_wn1:
            continue
        else:
            # Sort based on wc sequence.
            if mode == 'test':
                idx = argsort(array(g_wc1))

                g_wo1_s = array(g_wo1)[idx]
                g_wo1_s = list(g_wo1_s)
            elif mode == 'train':
                # due to teacher forcing, no need to sort.
                g_wo1_s = g_wo1
            else:
                raise ValueError

            if type(pr_wo1) != list:
                raise TypeError
            if g_wo1_s == pr_wo1:
                cnt += 1
    return cnt


def get_cnt_wo_list(g_wn, g_wc, g_wo, pr_wc, pr_wo, mode):
    """ pr's are all sorted as pr_wc are sorted in increasing order (in column idx)
        However, g's are not sorted.

        Sort g's in increasing order (in column idx)
    """
    cnt_list = []
    for b, g_wo1 in enumerate(g_wo):
        g_wc1 = g_wc[b]
        pr_wc1 = pr_wc[b]
        pr_wo1 = pr_wo[b]
        pr_wn1 = len(pr_wo1)
        g_wn1 = g_wn[b]

        if g_wn1 != pr_wn1:
            cnt_list.append(0)
            continue
        else:
            # Sort based wc sequence.
            if mode == 'test':
                idx = argsort(array(g_wc1))

                g_wo1_s = array(g_wo1)[idx]
                g_wo1_s = list(g_wo1_s)
            elif mode == 'train':
                # due to tearch forcing, no need to sort.
                g_wo1_s = g_wo1
            else:
                raise ValueError

            if type(pr_wo1) != list:
                raise TypeError

            if g_wo1_s == pr_wo1:
                cnt_list.append(1)
            else:
                cnt_list.append(0)
    return cnt_list


def get_cnt_wv(g_wn, g_wc, g_wvi, pr_wvi, mode):
    """ usalbe only when g_wc was used to find pr_wv

    g_wvi
    """
    cnt = 0
    for b, g_wvi1 in enumerate(g_wvi):
        pr_wvi1 = pr_wvi[b]
        g_wc1 = g_wc[b]
        pr_wn1 = len(pr_wvi1)
        g_wn1 = g_wn[b]

        # Now sorting.
        # Sort based wc sequence.
        if mode == 'test':
            idx1 = argsort(array(g_wc1))
        elif mode == 'train':
            idx1 = list(range(g_wn1))
        else:
            raise ValueError

        if g_wn1 != pr_wn1:
            continue
        else:
            flag = True
            for i_wn, idx11 in enumerate(idx1):
                g_wvi11 = g_wvi1[idx11]
                pr_wvi11 = pr_wvi1[i_wn]
                if g_wvi11 != pr_wvi11:
                    flag = False
                    break
            if flag:
                cnt += 1

    return cnt


def get_cnt_wvi_list(g_wn, g_wc, g_wvi, pr_wvi, mode):
    """ usalbe only when g_wc was used to find pr_wv
    """
    cnt_list = []
    for b, g_wvi1 in enumerate(g_wvi):
        g_wc1 = g_wc[b]
        pr_wvi1 = pr_wvi[b]
        pr_wn1 = len(pr_wvi1)
        g_wn1 = g_wn[b]

        # Now sorting.
        # Sort based wc sequence.
        if mode == 'test':
            idx1 = argsort(array(g_wc1))
        elif mode == 'train':
            idx1 = list(range(g_wn1))
        else:
            raise ValueError

        if g_wn1 != pr_wn1:
            cnt_list.append(0)
            continue
        else:
            flag = True
            for i_wn, idx11 in enumerate(idx1):
                g_wvi11 = g_wvi1[idx11]
                pr_wvi11 = pr_wvi1[i_wn]
                if g_wvi11 != pr_wvi11:
                    flag = False
                    break
            if flag:
                cnt_list.append(1)
            else:
                cnt_list.append(0)

    return cnt_list


def get_cnt_wv_list(g_wn, g_wc, g_sql_i, pr_sql_i, mode):
    """ usalbe only when g_wc was used to find pr_wv
    """
    cnt_list = []
    for b, g_wc1 in enumerate(g_wc):
        pr_wn1 = len(pr_sql_i[b]["conds"])
        g_wn1 = g_wn[b]

        # Now sorting.
        # Sort based wc sequence.
        if mode == 'test':
            idx1 = argsort(array(g_wc1))
        elif mode == 'train':
            idx1 = list(range(g_wn1))
        else:
            raise ValueError

        if g_wn1 != pr_wn1:
            cnt_list.append(0)
            continue
        else:
            flag = True
            for i_wn, idx11 in enumerate(idx1):
                g_wvi_str11 = str(g_sql_i[b]["conds"][idx11][2]).lower()
                if len(g_sql_i[b]["conds"][idx11]) > 3:
                    g_wvi_str11 = str(g_sql_i[b]["conds"][idx11][3]).lower()
                pr_wvi_str11 = str(pr_sql_i[b]["conds"][i_wn][2]).lower()
                if g_wvi_str11 != pr_wvi_str11:
                    flag = False
                    break
            if flag:
                cnt_list.append(1)
            else:
                cnt_list.append(0)

    return cnt_list


def get_cnt_sw(g_sc, g_sa, g_wn, g_wc, g_wo, g_wvi, pr_sc, pr_sa, pr_wn, pr_wc, pr_wo, pr_wvi, mode):
    """ usalbe only when g_wc was used to find pr_wv
    """
    cnt_sc = get_cnt_sc(g_sc, pr_sc)
    cnt_sa = get_cnt_sa(g_sa, pr_sa)
    cnt_wn = get_cnt_wn(g_wn, pr_wn)
    cnt_wc = get_cnt_wc(g_wc, pr_wc)
    cnt_wo = get_cnt_wo(g_wn, g_wc, g_wo, pr_wc, pr_wo, mode)
    cnt_wv = get_cnt_wv(g_wn, g_wc, g_wvi, pr_wvi, mode)

    return cnt_sc, cnt_sa, cnt_wn, cnt_wc, cnt_wo, cnt_wv


def get_cnt_sw_list(g_sc, g_cond_conn_op, g_sa, g_wn, g_wc, g_wo, g_wvi, g_slen,
                    pr_sc, pr_scco, pr_sa, pr_wn, pr_wc, pr_wo, pr_wvi,
                    g_sql_i, pr_sql_i,
                    mode):
    """ usalbe only when g_wc was used to find pr_wv
    """
    # cnt_sc = get_cnt_sc_list(g_sc, pr_sc)
    cnt_sc = get_cnt_wc_list(g_sc, pr_sc)

    cnt_scco = get_cnt_sc_list(g_cond_conn_op, pr_scco)

    # cnt_sa = get_cnt_sc_list(g_sa, pr_sa)
    cnt_sa = get_cnt_wo_list(g_slen, g_sc, g_sa, pr_sc, pr_sa, mode)

    cnt_wn = get_cnt_sc_list(g_wn, pr_wn)
    cnt_wc = get_cnt_wc_list(g_wc, pr_wc)
    cnt_wo = get_cnt_wo_list(g_wn, g_wc, g_wo, pr_wc, pr_wo, mode)
    if pr_wvi:
        cnt_wvi = get_cnt_wvi_list(g_wn, g_wc, g_wvi, pr_wvi, mode)
    else:
        cnt_wvi = [0] * len(cnt_sc)
    cnt_wv = get_cnt_wv_list(g_wn, g_wc, g_sql_i, pr_sql_i,
                             mode)  # compare using wv-str which presented in original data.

    return cnt_sc, cnt_scco, cnt_sa, cnt_wn, cnt_wc, cnt_wo, cnt_wvi, cnt_wv


def get_cnt_lx_list(cnt_sc1, cnt_cco1, cnt_sa1, cnt_wn1, cnt_wc1, cnt_wo1, cnt_wv1):
    # all cnt are list here.
    cnt_list = []
    cnt_lx = 0
    for csc, ccco, csa, cwn, cwc, cwo, cwv in zip(cnt_sc1, cnt_cco1, cnt_sa1, cnt_wn1, cnt_wc1, cnt_wo1, cnt_wv1):
        if csc and ccco and csa and cwn and cwc and cwo and cwv:
            cnt_list.append(1)
        else:
            cnt_list.append(0)

    return cnt_list


def get_cnt_x_list(engine, tb, g_sc, g_sa, g_sql_i, pr_sc, pr_sa, pr_sql_i):
    cnt_x1_list = []
    g_ans = []
    pr_ans = []
    for b in range(len(g_sc)):
        g_ans1 = engine.execute(tb[b]['id'], g_sc[b], g_sa[b], g_sql_i[b]['conds'])
        # print(f'cnt: {cnt}')
        # print(f"pr_sql_i: {pr_sql_i[b]['conds']}")
        try:
            pr_ans1 = engine.execute(tb[b]['id'], pr_sc[b], pr_sa[b], pr_sql_i[b]['conds'])

            if bool(pr_ans1):  # not empty due to lack of the data from incorretly generated sql
                if g_ans1 == pr_ans1:
                    cnt_x1 = 1
                else:
                    cnt_x1 = 0
            else:
                cnt_x1 = 0
        except:
            # type error etc... Execution-guided decoding may be used here.
            pr_ans1 = None
            cnt_x1 = 0
        cnt_x1_list.append(cnt_x1)
        g_ans.append(g_ans1)
        pr_ans.append(pr_ans1)

    return cnt_x1_list, g_ans, pr_ans


def get_mean_grad(named_parameters):
    """
    Get list of mean, std of grad of each parameters
    Code based on web searched result..
    """
    mu_list = []
    sig_list = []
    for name, param in named_parameters:
        if param.requires_grad:  # and ("bias" not in name) :
            # bias makes std = nan as it is of single parameters
            magnitude = param.grad.abs()
            mu_list.append(magnitude.mean())
            if len(magnitude) == 1:
                # why nan for single param? Anyway to avoid that..
                sig_list.append(torch.tensor(0))
            else:
                sig_list.append(magnitude.std())

            # if "svp_se"

    return mu_list, sig_list

def date(rows, nlu, idx):
    ret = ""

    items = []
    for i in rows:
        if idx < len(i):
            items.append(str(i[idx]))
        else:
            items.append(i[-1])

    nlu_date_norm = []
    
    date = re.compile(r'(\d{2})[\年](\d{1,2})[\月](\d{1,2})[\日\号]')
    nlu_date = date.findall(nlu)
    for u in nlu_date:
        nlu_date_norm.append((int(u[0]), int(u[1]), int(u[2])))
        
    date = re.compile(r'[^\年^\d](\d{1,2})[\月](\d{1,2})[\日\号]')
    nlu_date = date.findall(nlu)
    for u in nlu_date:
        nlu_date_norm.append((0, int(u[0]), int(u[1])))

    date = re.compile(r'(\d{2})[\年](\d{1,2})[\月][^\d]')
    nlu_date = date.findall(nlu)
    for u in nlu_date:
        nlu_date_norm.append((int(u[0]),int(u[1]),0))
        
    #print(nlu_date_norm)
    
    for item in items:
        item_re = re.compile(r'(\d{2})[-](\d{1,2})[-](\d{1,2})')
        item_date = item_re.findall(str(item))

        if len(item_date) != 1:
            continue
        for u in nlu_date_norm:
            if int(item_date[0][0]) != u[0] and u[0] != 0:
                continue
            if int(item_date[0][1]) != u[1] and u[1] != 0:
                continue
            if int(item_date[0][2]) != u[2] and u[2] != 0:
                continue
            return item, 1

    return ret, 0

def match_num(items, nlu):

    nlu_num = [int(u) for u in re.findall(r"[^\.\d](\d+)[^\.\d]", '@'+re.sub("[-]", "", nlu)+'@')] # int

    if len(nlu_num) == 0:
        return "", 0

    for j, item in enumerate(items):
        tp = [int(u) for u in re.findall(r"[^\.\d](\d+)[^\.\d]", '@'+re.sub("[-]", "", str(item))+'@')]
        if len(tp) != 1:
            continue
        if tp[0] in nlu_num:
            return item, j
        if len(str(tp[0])) >= 10:
            continue
        ss = num2char(str(tp[0]))
        if ss == "":
            continue
        if nlu.find(ss) != -1:
            return item, j
    return "", 0

def sim_sort1(rows, nlu, wv, idx, used):
    ret = ""
    same = -1
    ret_idx = 0
    items = []
    for i in rows:
        if idx < len(i):
            items.append(str(i[idx]))
        else:
            items.append(i[-1])

    for j, i in enumerate(items):
        if i in used:
            continue
        samei = 0.0
        for char in str(i):
            if char in nlu:
                samei += 1
        if (samei/len(str(i))) >= same and len(str(i)) < 20:
            if (samei/len(str(i))) == same and len(str(i)) < len(str(ret)):
                continue
            ret = i
            ret_idx = j
            same = samei/len(str(i))
    return ret, same, j


def sim_sort2(rows, nlu, wv, idx, used):

    ret = ""
    same = -1
    ret_idx = 0

    nlu= re.sub(r"[,]", "", nlu)
    nlu= re.sub(r"[ ]", "", nlu)

    wv = ''.join(wv).replace('##', '')

    items = []

    for i in rows:
        if idx < len(i):
            items.append(i[idx])
        else:
            items.append(i[-1])

    # for j, i in enumerate(items):
    #     if i in used:
    #         continue
    #     if nlu.find(str(i)) != -1:
    #         return i, 1, j

    nlu= nlu.replace('湖南', '芒果TV湖南')
    nlu= re.sub(r"[\鹅]", r"腾讯", nlu)

    ret, ret_idx = match_num(items, nlu)
    if ret != "":
        return ret, 1, ret_idx

    for j, i in enumerate(items):
        if i in used:
            continue
        im = difflib.SequenceMatcher(None, wv, str(i)).quick_ratio()
        # print(im, wv, str(i), same, ret_idx)
        if im > same:
            same = im
            ret = str(i)
            ret_idx = j
        if type(i) is not str:
            try:
                im = difflib.SequenceMatcher(None, wv, num2char(str(i).replace('-', ''))).quick_ratio()
                if im > same:
                    same = im
                    ret = str(i)
                    ret_idx = j
            except:
                pass
                #print(i)
    if same >= 0.5:
        return ret, same, ret_idx

    return "", same, j


def sim_sort3(rows, nlu, idx, used):
    ret = ""
    same = -1
    nlu = ''.join(nlu).replace('##', '')
    nlu = nlu.replace('两', '二')
    # print(nlu)
    ret_idx = 0

    items = []

    for i in rows:
        if idx < len(i):
            try:
                if abs(float(i[idx]) - int(i[idx])) < 1e-5:
                    i[idx] = int(i[idx])
            except:
                pass
            items.append(i[idx])
        else:
            try:
                if abs(float(i[-1]) - int(i[-1])) < 1e-5:
                    i[-1] = int(i[-1])
            except:
                pass
            items.append(i[-1])

    for j, i in enumerate(items):
        if i in used:
            continue
        if nlu.find(str(i)) != -1:
            # print(nlu, i)
            return i, 1, j

    for j, i in enumerate(items):
        if i in used:
            continue
        im = difflib.SequenceMatcher(None, nlu, str(i)).quick_ratio()
        # print(im, nlu, str(i), same)
        if im > same:
            same = im
            ret = str(i)
            ret_idx = j
            # print('max', j)
        # print(num2char(str(i).replace('-', '')))
        try:
            i = float(i)
            if float(i) - int(i) < e-5:
                i = int(i)
        except:
            pass
        if type(i) is not str:
            try:
                im = difflib.SequenceMatcher(None, nlu, num2char(str(i).replace('-', ''))).quick_ratio()
                # print(num2char(str(i).replace('-', '')))
                if im > same:
                    same = im
                    ret = str(i)
                    ret_idx = j
            except:
                pass
        try:
            if abs(float(i) - float(nlu)) < e-5:
                return str(i), 1, j
            #print(i)
        except:
            pass

    return ret, same, ret_idx


def num2char(num):
    num_dict = {'1':'一', '2':'二', '3':'三', '4':'四', '5':'五', '6':'六', '7':'七', '8':'八', '9':'九', '0':'零', }
    index_dict = {1:'', 2:'十', 3:'百', 4:'千', 5:'万', 6:'十', 7:'百', 8:'千', 9:'亿'}
    num = num.strip()
    num = re.sub('[%]', '', num)
    # nums = list(num)
    num = re.split('[.]', num)
    num_p1, num_p2 = None, None
    if len(num) == 1:
        num_p1 = num[0]
    elif len(num) == 2:
        num_p1, num_p2 = num[0], num[1]
    # for i in num:
    #     if i !=
    nums_1 = num_p1
    nums_index = [x for x in range(1, len(num_p1)+1)][-1::-1]

    str1 = ''
    for index, item in enumerate(num_p1):
        str1 = "".join((str1, num_dict[item], index_dict[nums_index[index]]))

    str1 = re.sub("零[十百千零]*", "零", str1)
    str1 = re.sub("零万", "万", str1)
    str1 = re.sub("亿万", "亿零", str1)
    str1 = re.sub("零零", "零", str1)
    str1 = re.sub("零\\b" , "", str1)
    if num_p2 is not None:
        str1 = "".join((str1, "点"))
        for index, item in enumerate(num_p2):
            str1 = "".join((str1, num_dict[item]))
    return str1

def generate_sql_i(pr_sc, pr_scco, pr_sa, pr_wn, pr_wc, pr_wo, pr_wv_str, nlu, t, table):
    # print("((((((")
    pr_sql_i = []
    for b, nlu1 in enumerate(nlu):
        tid1 = t[b]['table_id']
        tab = table[tid1]
        conds = []
        for i_wn in range(pr_wn[b]):
            conds1 = [pr_wc[b][i_wn], pr_wo[b][i_wn], str(''.join(pr_wv_str[b][i_wn]).replace('##', ''))]
            conds.append(conds1)
        if len(conds) == 1:
            pr_scco[b] = 0
        if len(conds) == 1 and pr_wc[b][0] == len(tab['header'])-1:
            conds = [[len(tab['header'])-1, 2, 'Null']]
            pr_scco[b] = 0
        pr_sql_i1 = {'agg': pr_sa[b], 'cond_conn_op': pr_scco[b], 'sel': pr_sc[b], 'conds': conds}
        pr_sql_i.append(pr_sql_i1)
    return pr_sql_i

# def generate_sql_i(pr_sc, pr_scco, pr_sa, pr_wn, pr_wc, pr_wo, pr_wv_str, nlu, t, table):
#     # print("((((((")
#     pr_sql_i = []
#     for b, nlu1 in enumerate(nlu):
#         tid1 = t[b]['table_id']
#         tab = table[tid1]
#         rows = deepcopy(tab['rows'])
# 
#         # add null
#         for i, row in enumerate(rows):
#             row.append('null')
#             rows[i] = row
# 
#         rows_uc = deepcopy(rows)
#         # print(pr_wc)
#         # deal rows in uncased format
#         for i, row in enumerate(rows_uc):
#             for j, item in enumerate(row):
#                 if type(item) is str:
#                     row[j] = item.lower()
#             rows_uc[i] = row
#         # print(rows)
#         # print(nlu1)
#         # print("=======")
#         # print(items)
# 
#         conds = []
#         conds_s = set()
#         used = []
#         tmp = ""
# 
#         for i_wn in range(pr_wn[b]):
#             conds1 = []
#             q = 0
#             fff = 0
#             if pr_wo[b][i_wn] == 2 or pr_wo[b][i_wn] == 3:
#                 merged_wv11, same = date(rows_uc, nlu1, pr_wc[b][i_wn])
#                 # print(1, merged_wv11)
# 
#                 if merged_wv11 == "":
#                     merged_wv11, same, j = sim_sort3(rows_uc, pr_wv_str[b][i_wn], pr_wc[b][i_wn], used)
#                     merged_wv11 = rows[j][pr_wc[b][i_wn]]
#                     # print(pr_wc[b][i_wn])
#                     # print(2, merged_wv11, same)
#                     try:
#                         if abs(float(merged_wv11) - int(merged_wv11)) < 1e-5:
#                             merged_wv11 = int(merged_wv11)
#                     except:
#                         pass
#                     if same < 0.3:
#                         # 扩张搜索
#                         q = 0
#                         q_max = 0
#                         j_max = 0
#                         fff = -1
#                         while q < len(rows[0]):
#                             _, same1, j = sim_sort2(rows_uc, nlu1, pr_wv_str[b][i_wn], q, [])
#                             if same1 > same:
#                                 same = same1
#                                 q_max = q
#                                 j_max = j
#                             # print(j_max)
#                             # print(3, q, same1, rows[j_max][q_max])
#                             q += 1
#                         merged_wv11 = rows[j_max][q_max]
#                         # print(3, q, same, merged_wv11)
#                         try:
#                             if abs(float(merged_wv11) - int(merged_wv11)) < 1e-5:
#                                 merged_wv11 = int(merged_wv11)
#                         except:
#                             pass
#                         '''
#                         if tmp != merged_wv11 or q != pr_wc[b][i_wn]:
#                             print("=========")
#                             print(nlu1)
#                             print("q:", q, "pr_wc:", pr_wc[b][i_wn])
#                             print("wv:", ''.join(pr_wv_str[b][i_wn]).replace('##', ''))
#                             print("pre:", merged_wv11)
#                             print("post:", tmp)
#                         '''
#                         # merged_wv11 = tmp
# 
#                 if merged_wv11 == "":
#                     fff = 0
#                     merged_wv11, _, j = sim_sort1(rows_uc, nlu1, pr_wv_str[b][i_wn], pr_wc[b][i_wn], used)
#                     merged_wv11 = rows[j][pr_wc[b][i_wn]]
#                     # print(5, merged_wv11)
#                     try:
#                         if abs(float(merged_wv11) - int(merged_wv11)) < 1e-5:
#                             merged_wv11 = int(merged_wv11)
#                     except:
#                         pass
#                     #print("mine_2:", merged_wv11)
# 
#                 # used.append(str(merged_wv11))
#                 # try:
#                 #     x = float(pr_wv_str[b][i_wn])
#                 #     if abs(float(x) - int(x)) < 1e-5:
#                 #         merged_wv11 = int(x)
#                 #     else:
#                 #         merged_wv11 = float(x)
#                 #     print(6, merged_wv11)
#                 # except:
#                 #     pass
# 
#             else:
#                 merged_wv11 = ''.join(pr_wv_str[b][i_wn]).replace('##', '')
#                 # print(6, merged_wv11)
#                 if re.search('[零一二两三四五六七八九十点]', merged_wv11):
#                     merged_wv11 = merged_wv11.replace('两', '二')
#                     try:
#                         merged_wv11 = str(chn_to_sum(merged_wv11))
#                     except:
#                         pass
# 
#             used.append(str(merged_wv11))
#             if fff == -1:
#                 conds1.append(q_max)
#             else:
#                 conds1.append(pr_wc[b][i_wn])
#             conds1.append(pr_wo[b][i_wn])
# 
#             conds1.append(str(merged_wv11))
#             if (conds1 in conds) is False:
#                 conds.append(conds1)
#             # print(conds)
#             # print(pr_wv_str[b][i_wn])
#         # conds = list(set(conds))
#         if len(conds) == 1:
#             pr_scco[b] = 0
#         if len(conds) == 1 and pr_wc[b][0] == len(tab['header'])-1:
#             conds = [[len(tab['header'])-1, 2, 'Null']]
#             pr_scco[b] = 0
#         pr_sql_i1 = {'agg': pr_sa[b], 'cond_conn_op': pr_scco[b], 'sel': pr_sc[b], 'conds': conds}
#         pr_sql_i.append(pr_sql_i1)
#     return pr_sql_i


def save_for_evaluation(path_save, results, dset_name):
    path_save_file = os.path.join(path_save, f'results_{dset_name}.json')
    # if not os.path.exists(path_save_file):
    #     os.mknod(path_save_file)

    with open(path_save_file, 'w', encoding='utf-8') as f:
        for i, r1 in enumerate(results):
            json_str = json.dumps(r1['query'], ensure_ascii=False, default=json_default_type_checker)
            json_str += '\n'

            f.writelines(json_str)
    return path_save_file


def save_for_evaluation_aux(path_save, results, dset_name, ):
    path_save_file = os.path.join(path_save, f'results_aux_{dset_name}.jsonl')
    with open(path_save_file, 'w', encoding='utf-8') as f:
        for i, r1 in enumerate(results):
            json_str = json.dumps(r1, ensure_ascii=False, default=json_default_type_checker)
            json_str += '\n'

            f.writelines(json_str)


def check_sc_sa_pairs(tb, pr_sc, pr_sa, ):
    """
    Check whether pr_sc, pr_sa are allowed pairs or not.
    agg_ops = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']

    """
    bS = len(pr_sc)
    check = [False] * bS
    for b, pr_sc1 in enumerate(pr_sc):
        pr_sa1 = pr_sa[b]
        hd_types1 = tb[b]['types']
        hd_types11 = hd_types1[pr_sc1]
        if hd_types11 == 'text':
            if pr_sa1 == 0 or pr_sa1 == 3:  # ''
                check[b] = True
            else:
                check[b] = False

        elif hd_types11 == 'real':
            check[b] = True
        else:
            raise Exception("New TYPE!!")

    return check


def remap_sc_idx(idxs, pr_sc_beam):
    for b, idxs1 in enumerate(idxs):
        for i_beam, idxs11 in enumerate(idxs1):
            sc_beam_idx = idxs[b][i_beam][0]
            sc_idx = pr_sc_beam[b][sc_beam_idx]
            idxs[b][i_beam][0] = sc_idx

    return idxs


def sort_and_generate_pr_w(pr_sql_i):
    pr_wc = []
    pr_wo = []
    pr_wv = []
    for b, pr_sql_i1 in enumerate(pr_sql_i):
        conds1 = pr_sql_i1["conds"]
        pr_wc1 = []
        pr_wo1 = []
        pr_wv1 = []

        # Generate
        for i_wn, conds11 in enumerate(conds1):
            pr_wc1.append(conds11[0])
            pr_wo1.append(conds11[1])
            pr_wv1.append(conds11[2])

        # sort based on pr_wc1
        idx = argsort(pr_wc1)
        pr_wc1 = array(pr_wc1)[idx].tolist()
        pr_wo1 = array(pr_wo1)[idx].tolist()
        pr_wv1 = array(pr_wv1)[idx].tolist()

        conds1_sorted = []
        for i, idx1 in enumerate(idx):
            conds1_sorted.append(conds1[idx1])

        pr_wc.append(pr_wc1)
        pr_wo.append(pr_wo1)
        pr_wv.append(pr_wv1)

        pr_sql_i1['conds'] = conds1_sorted

    return pr_wc, pr_wo, pr_wv, pr_sql_i


def generate_sql_q(sql_i, tb):
    sql_q = []
    for b, sql_i1 in enumerate(sql_i):
        tb1 = tb[b]
        sql_q1 = generate_sql_q1(sql_i1, tb1)
        sql_q.append(sql_q1)

    return sql_q


def generate_sql_q1(sql_i1, tb1):
    """
        sql = {'sel': 5, 'agg': 4, 'conds': [[3, 0, '59']]}
        agg_ops = ['', 'max', 'min', 'count', 'sum', 'avg']
        cond_ops = ['=', '>', '<', 'OP']

        Temporal as it can show only one-time conditioned case.
        sql_query: real sql_query
        sql_plus_query: More redable sql_query

        "PLUS" indicates, it deals with the some of db specific facts like PCODE <-> NAME
    """
    # print(sql_i1)
    agg_ops = ['', 'avg', 'max', 'min', 'count', 'sum']
    cond_ops = ['>', '<', '==', '!=']
    cond_conn_op = ['', 'and', 'or']
    headers = tb1["header"]
    # select_header = headers[sql['sel']].lower()
    # try:
    #     select_table = tb1["name"]
    # except:
    #     print(f"No table name while headers are {headers}")
    select_table = tb1["tablename"]

    select_agg = [agg_ops[sql_i1['agg'][v]] for v in range(len(sql_i1['agg']))]
    select_header = [headers[sql_i1['sel'][v]] for v in range(len(sql_i1['sel']))]

    sql_query_part1 = f'SELECT {select_agg}({select_header}) '

    where_num = len(sql_i1['conds'])
    if where_num == 0:
        sql_query_part2 = f'FROM {select_table}'
        # sql_plus_query_part2 = f'FROM {select_table}'

    else:
        sql_query_part2 = f'FROM {select_table} WHERE'
        # sql_plus_query_part2 = f'FROM {select_table_refined} WHERE'
        # ----------------------------------------------------------------------------------------------------------
        for i in range(where_num):
            # check 'OR'
            # number_of_sub_conds = len(sql['conds'][i])
            where_header_idx, where_op_idx, where_str = sql_i1['conds'][i]
            where_header = headers[where_header_idx]
            where_op = cond_ops[where_op_idx]
            if i > 0:
                sql_query_part2 += ' AND'
                # sql_plus_query_part2 += ' AND'

            sql_query_part2 += f" {where_header} {where_op} {where_str}"

    sql_query = sql_query_part1 + sql_query_part2
    # sql_plus_query = sql_plus_query_part1 + sql_plus_query_part2

    return sql_query


def get_pnt_idx1(col_pool_type, st_ed):
    st, ed = st_ed
    if col_pool_type == 'start_tok':
        pnt_idx1 = st
    elif col_pool_type == 'end_tok':
        pnt_idx1 = ed
    elif col_pool_type == 'avg':
        pnt_idx1 = arange(st, ed, 1)
    return pnt_idx1


def gen_g_pnt_idx(g_wvi, sql_i, i_hds, i_sql_vocab, col_pool_type):
    """
    sql_vocab = (
        0.. "sql none", "sql max", "sql min", "sql count", "sql sum", "sql average", ..5
        6.. "sql select", "sql where", "sql and", .. 8
        9.. "sql equal", "sql greater than", "sql less than", .. 11
        12.. "sql start", "sql end" .. 13
    )
    """
    g_pnt_idxs = []

    for b, sql_i1 in enumerate(sql_i):
        i_sql_vocab1 = i_sql_vocab[b]
        i_hds1 = i_hds[b]
        g_pnt_idxs1 = []

        # start token
        pnt_idx1 = get_pnt_idx1(col_pool_type, i_sql_vocab1[-2])
        g_pnt_idxs1.append(pnt_idx1)

        # select token
        pnt_idx1 = get_pnt_idx1(col_pool_type, i_sql_vocab1[6])
        g_pnt_idxs1.append(pnt_idx1)

        # select agg
        idx_agg = sql_i1["agg"]
        pnt_idx1 = get_pnt_idx1(col_pool_type, i_sql_vocab1[idx_agg])
        g_pnt_idxs1.append(pnt_idx1)

        # select column
        idx_sc = sql_i1["sel"]
        pnt_idx1 = get_pnt_idx1(col_pool_type, i_hds1[idx_sc])
        g_pnt_idxs1.append(pnt_idx1)

        conds = sql_i1["conds"]
        wn = len(conds)
        if wn <= 0:
            pass
        else:
            # select where
            pnt_idx1 = get_pnt_idx1(col_pool_type, i_sql_vocab1[7])
            g_pnt_idxs1.append(pnt_idx1)

            for i_wn, conds1 in enumerate(conds):
                # where column
                idx_wc = conds1[0]
                pnt_idx1 = get_pnt_idx1(col_pool_type, i_hds1[idx_wc])
                g_pnt_idxs1.append(pnt_idx1)

                # where op
                idx_wo = conds1[1]
                pnt_idx1 = get_pnt_idx1(col_pool_type, i_sql_vocab1[idx_wo + 9])
                g_pnt_idxs1.append(pnt_idx1)

                # where val
                st, ed = g_wvi[b][i_wn]
                end_pos_of_sql_vocab = i_sql_vocab1[-1][-1]
                g_pnt_idxs1.append(st + 1 + end_pos_of_sql_vocab)  # due to inital [CLS] token in BERT-input vector
                g_pnt_idxs1.append(ed + 1 + end_pos_of_sql_vocab)  # due to inital [CLS] token in BERT-input vector

                # and token
                if i_wn < wn - 1:
                    pnt_idx1 = get_pnt_idx1(col_pool_type, i_sql_vocab1[8])
                    g_pnt_idxs1.append(pnt_idx1)

        # end token
        pnt_idx1 = get_pnt_idx1(col_pool_type, i_sql_vocab1[-1])
        g_pnt_idxs1.append(pnt_idx1)

        g_pnt_idxs.append(g_pnt_idxs1)

    return g_pnt_idxs


def pred_pnt_idxs(score, pnt_start_tok, pnt_end_tok):
    pr_pnt_idxs = []
    for b, score1 in enumerate(score):
        # score1 = [T, max_seq_length]
        pr_pnt_idxs1 = [pnt_start_tok]
        for t, score11 in enumerate(score1):
            pnt = score11.argmax().item()
            pr_pnt_idxs1.append(pnt)

            if pnt == pnt_end_tok:
                break
        pr_pnt_idxs.append(pr_pnt_idxs1)

    return pr_pnt_idxs


def generate_sql_q_s2s(pnt_idxs, tokens, tb):
    sql_q = []
    for b, pnt_idxs1 in enumerate(pnt_idxs):
        tb1 = tb[b]
        sql_q1 = generate_sql_q1_s2s(pnt_idxs1, tokens[b], tb1)
        sql_q.append(sql_q1)

    return sql_q


def generate_sql_q1_s2s(pnt_idxs1, tokens1, tb1):
    """
        agg_ops = ['', 'max', 'min', 'count', 'sum', 'avg']
        cond_ops = ['=', '>', '<', 'OP']

        Temporal as it can show only one-time conditioned case.
        sql_query: real sql_query
        sql_plus_query: More redable sql_query

        "PLUS" indicates, it deals with the some of db specific facts like PCODE <-> NAME
    """
    sql_query = ""
    for t, pnt_idxs11 in enumerate(pnt_idxs1):
        tok = tokens1[pnt_idxs11]
        sql_query += tok
        if t < len(pnt_idxs1) - 1:
            sql_query += " "

    return sql_query


# Generate sql_i from pnt_idxs
def find_where_pnt_belong(pnt, vg):
    idx_sub = -1
    for i, st_ed in enumerate(vg):
        st, ed = st_ed
        if pnt < ed and pnt >= st:
            idx_sub = i

    return idx_sub


def gen_pnt_i_from_pnt(pnt, i_sql_vocab1, i_nlu1, i_hds1):
    # Find where it belong
    vg_list = [i_sql_vocab1, [i_nlu1], i_hds1]  # as i_nlu has only single st and ed
    i_vg = -1
    i_vg_sub = -1
    for i, vg in enumerate(vg_list):
        idx_sub = find_where_pnt_belong(pnt, vg)
        if idx_sub > -1:
            i_vg = i
            i_vg_sub = idx_sub
            break
    return i_vg, i_vg_sub


def gen_i_vg_from_pnt_idxs(pnt_idxs, i_sql_vocab, i_nlu, i_hds):
    i_vg_list = []
    i_vg_sub_list = []
    for b, pnt_idxs1 in enumerate(pnt_idxs):
        # if properly generated,
        sql_q1_list = []
        i_vg_list1 = []  # index of (sql_vocab, nlu, hds)
        i_vg_sub_list1 = []  # index inside of each vocab group

        for t, pnt in enumerate(pnt_idxs1):
            i_vg, i_vg_sub = gen_pnt_i_from_pnt(pnt, i_sql_vocab[b], i_nlu[b], i_hds[b])
            i_vg_list1.append(i_vg)
            i_vg_sub_list1.append(i_vg_sub)

        # sql_q1 = sql_q1.join(' ')
        # sql_q.append(sql_q1)
        i_vg_list.append(i_vg_list1)
        i_vg_sub_list.append(i_vg_sub_list1)
    return i_vg_list, i_vg_sub_list


def gen_sql_q_from_i_vg(tokens, nlu, nlu_t, hds, tt_to_t_idx, pnt_start_tok, pnt_end_tok, pnt_idxs, i_vg_list,
                        i_vg_sub_list):
    """
    (
        "none", "max", "min", "count", "sum", "average",
        "select", "where", "and",
        "equal", "greater than", "less than",
        "start", "end"
    ),
    """
    sql_q = []
    sql_i = []
    for b, nlu_t1 in enumerate(nlu_t):
        sql_q1_list = []
        sql_i1 = {}
        tt_to_t_idx1 = tt_to_t_idx[b]
        nlu_st_observed = False
        agg_observed = False
        wc_obs = False
        wo_obs = False
        conds = []

        for t, i_vg in enumerate(i_vg_list[b]):
            i_vg_sub = i_vg_sub_list[b][t]
            pnt = pnt_idxs[b][t]
            if i_vg == 0:
                # sql_vocab
                if pnt == pnt_start_tok or pnt == pnt_end_tok:
                    pass
                else:
                    tok = tokens[b][pnt]
                    if tok in ["none", "max", "min", "count", "sum", "average"]:
                        agg_observed = True
                        if tok == "none":
                            pass
                        sql_i1["agg"] = ["none", "max", "min", "count", "sum", "average"].index(tok)
                    else:
                        if tok in ["greater", "less", "equal"]:
                            if tok == 'greater':
                                tok = '>'
                            elif tok == 'less':
                                tok = '<'
                            elif tok == 'equal':
                                tok = '='

                            # gen conds1
                            if wc_obs:
                                conds1.append(['=', '>', '<'].index(tok))
                                wo_obs = True

                        sql_q1_list.append(tok)

            elif i_vg == 1:
                # nlu case
                if not nlu_st_observed:
                    idx_nlu_st = pnt
                    nlu_st_observed = True
                else:
                    # now to wrap up
                    idx_nlu_ed = pnt
                    st_wh_idx = tt_to_t_idx1[idx_nlu_st - pnt_end_tok - 2]
                    ed_wh_idx = tt_to_t_idx1[idx_nlu_ed - pnt_end_tok - 2]
                    pr_wv_str11 = nlu_t1[st_wh_idx:ed_wh_idx + 1]
                    merged_wv11 = merge_wv_t1_eng(pr_wv_str11, nlu[b])
                    sql_q1_list.append(merged_wv11)
                    nlu_st_observed = False

                    if wc_obs and wo_obs:
                        conds1.append(merged_wv11)
                        conds.append(conds1)

                        wc_obs = False
                        wo_obs = False


            elif i_vg == 2:
                # headers
                tok = hds[b][i_vg_sub]
                if agg_observed:
                    sql_q1_list.append(f"({tok})")
                    sql_i1["sel"] = i_vg_sub
                    agg_observed = False
                else:
                    wc_obs = True
                    conds1 = [i_vg_sub]

                    sql_q1_list.append(tok)

        # insert table name between.
        sql_i1["conds"] = conds
        sql_i.append(sql_i1)
        sql_q1 = ' '.join(sql_q1_list)
        sql_q.append(sql_q1)

    return sql_q, sql_i


def get_cnt_lx_list_s2s(g_pnt_idxs, pr_pnt_idxs):
    # all cnt are list here.
    cnt_list = []
    for b, g_pnt_idxs1 in enumerate(g_pnt_idxs):
        pr_pnt_idxs1 = pr_pnt_idxs[b]

        if g_pnt_idxs1 == pr_pnt_idxs1:
            cnt_list.append(1)
        else:
            cnt_list.append(0)

    return cnt_list


def get_wemb_h_FT_Scalar_1(i_hds, l_hs, hS, all_encoder_layer, col_pool_type='start_tok'):
    """
    As if
    [ [table-1-col-1-tok1, t1-c1-t2, ...],
       [t1-c2-t1, t1-c2-t2, ...].
       ...
       [t2-c1-t1, ...,]
    ]

    # i_hds = [ [  Batch 1 ] [  Batch 2  ] ]
    #  [Batch 1] = [ (col1_st_idx, col1_ed_idx), (col2_st_idx, col2_ed_idx), ...]
    # i_hds = [[(11, 14), (15, 19), (20, 21), (22, 24), (25, 27), (28, 29)],
            #  [(16, 19), (20, 24), (25, 26), (27, 29), (30, 32), (33, 34)]]

    pool_type = 'start_tok', 'end_tok', 'avg'

    """
    bS = len(l_hs)
    l_hs_max = max(l_hs)
    wemb_h = torch.zeros([bS, l_hs_max, hS]).to(device)
    for b, i_hds1 in enumerate(i_hds):
        for i_hd, st_ed_pair in enumerate(i_hds1):
            st, ed = st_ed_pair
            if col_pool_type == 'start_tok':
                vec = all_encoder_layer[-1][b, st, :]
            elif col_pool_type == 'end_tok':
                vec = all_encoder_layer[-1][b, ed, :]
            elif col_pool_type == 'avg':
                vecs = all_encoder_layer[-1][b, st:ed, :]
                vec = vecs.mean(dim=1, keepdim=True)
            else:
                raise ValueError
            wemb_h[b, i_hd, :] = vec

    return wemb_h


def cal_prob(s_sc, s_sa, s_wn, s_wc, s_wo, s_wv, pr_sc, pr_sa, pr_wn, pr_wc, pr_wo, pr_wvi):
    """

    :param s_sc: [B, l_h]
    :param s_sa: [B, l_a] # 16
    :param s_wn: [B, 5]
    :param s_wc: [B, l_h]
    :param s_wo: [B, 4, l_o] #
    :param s_wv: [B, 4, 22]
    :return:
    """
    # First get selected index

    #

    # Predict prob
    p_sc = cal_prob_sc(s_sc, pr_sc)
    p_sa = cal_prob_sa(s_sa, pr_sa)
    p_wn = cal_prob_wn(s_wn, pr_wn)
    p_wc = cal_prob_wc(s_wc, pr_wc)
    p_wo = cal_prob_wo(s_wo, pr_wo)
    p_wvi = cal_prob_wvi_se(s_wv, pr_wvi)

    # calculate select-clause probability
    p_select = cal_prob_select(p_sc, p_sa)

    # calculate where-clause probability
    p_where = cal_prob_where(p_wn, p_wc, p_wo, p_wvi)

    # calculate total probability
    p_tot = cal_prob_tot(p_select, p_where)

    return p_tot, p_select, p_where, p_sc, p_sa, p_wn, p_wc, p_wo, p_wvi


def cal_prob_tot(p_select, p_where):
    p_tot = []
    for b, p_select1 in enumerate(p_select):
        p_where1 = p_where[b]
        p_tot.append(p_select1 * p_where1)

    return p_tot


def cal_prob_select(p_sc, p_sa):
    p_select = []
    for b, p_sc1 in enumerate(p_sc):
        p1 = 1.0
        p1 *= p_sc1
        p1 *= p_sa[b]

        p_select.append(p1)
    return p_select


def cal_prob_where(p_wn, p_wc, p_wo, p_wvi):
    p_where = []
    for b, p_wn1 in enumerate(p_wn):
        p1 = 1.0
        p1 *= p_wn1
        p_wc1 = p_wc[b]

        for i_wn, p_wc11 in enumerate(p_wc1):
            p_wo11 = p_wo[b][i_wn]
            p_wv11_st, p_wv11_ed = p_wvi[b][i_wn]

            p1 *= p_wc11
            p1 *= p_wo11
            p1 *= p_wv11_st
            p1 *= p_wv11_ed

        p_where.append(p1)

    return p_where


def cal_prob_sc(s_sc, pr_sc):
    ps = F.softmax(s_sc, dim=1)
    p = []
    for b, ps1 in enumerate(ps):
        pr_sc1 = pr_sc[b]
        p1 = ps1[pr_sc1]
        p.append(p1.item())

    return p


def cal_prob_sa(s_sa, pr_sa):
    ps = F.softmax(s_sa, dim=1)
    p = []
    for b, ps1 in enumerate(ps):
        pr_sa1 = pr_sa[b]
        p1 = ps1[pr_sa1]
        p.append(p1.item())

    return p


def cal_prob_wn(s_wn, pr_wn):
    ps = F.softmax(s_wn, dim=1)
    p = []
    for b, ps1 in enumerate(ps):
        pr_wn1 = pr_wn[b]
        p1 = ps1[pr_wn1]
        p.append(p1.item())

    return p


def cal_prob_wc(s_wc, pr_wc):
    ps = torch.sigmoid(s_wc)
    ps_out = []
    for b, pr_wc1 in enumerate(pr_wc):
        ps1 = array(ps[b].cpu())
        ps_out1 = ps1[pr_wc1]
        ps_out.append(list(ps_out1))

    return ps_out


def cal_prob_wo(s_wo, pr_wo):
    # assume there is always at least single condition.
    ps = F.softmax(s_wo, dim=2)
    ps_out = []

    for b, pr_wo1 in enumerate(pr_wo):
        ps_out1 = []
        for n, pr_wo11 in enumerate(pr_wo1):
            ps11 = ps[b][n]
            ps_out1.append(ps11[pr_wo11].item())

        ps_out.append(ps_out1)

    return ps_out


def cal_prob_wvi_se(s_wv, pr_wvi):
    prob_wv = F.softmax(s_wv, dim=-2).detach().to('cpu').numpy()
    p_wv = []
    for b, pr_wvi1 in enumerate(pr_wvi):
        p_wv1 = []
        for i_wn, pr_wvi11 in enumerate(pr_wvi1):
            st, ed = pr_wvi11
            p_st = prob_wv[b, i_wn, st, 0]
            p_ed = prob_wv[b, i_wn, ed, 1]
            p_wv1.append([p_st, p_ed])
        p_wv.append(p_wv1)

    return p_wv


def generate_inputs_s2s(tokenizer, nlu1_tt, hds1, sql_vocab1):
    """
    [CLS] sql_vocab [SEP] question [SEP] headers
    To make sql_vocab in a fixed position.
    """

    tokens = []
    segment_ids = []

    tokens.append("[CLS]")

    # sql_vocab
    i_sql_vocab = []
    # for doc
    for i, sql_vocab11 in enumerate(sql_vocab1):
        i_st_sql = len(tokens)
        sub_tok = tokenizer.tokenize(sql_vocab11)
        tokens += sub_tok
        i_ed_sql = len(tokens)
        i_sql_vocab.append((i_st_sql, i_ed_sql))
        segment_ids += [1] * len(sub_tok)
        if i < len(sql_vocab1) - 1:
            tokens.append("[SEP]")
            segment_ids.append(0)
        elif i == len(sql_vocab1) - 1:
            tokens.append("[SEP]")
            segment_ids.append(1)
        else:
            raise EnvironmentError

    # question
    i_st_nlu = len(tokens)  # to use it later

    segment_ids.append(0)
    for token in nlu1_tt:
        tokens.append(token)
        segment_ids.append(0)
    i_ed_nlu = len(tokens)
    tokens.append("[SEP]")
    segment_ids.append(0)
    i_nlu = (i_st_nlu, i_ed_nlu)

    # headers
    i_hds = []
    # for doc
    for i, hds11 in enumerate(hds1):
        i_st_hd = len(tokens)
        sub_tok = tokenizer.tokenize(hds11)
        tokens += sub_tok
        i_ed_hd = len(tokens)
        i_hds.append((i_st_hd, i_ed_hd))
        segment_ids += [1] * len(sub_tok)
        if i < len(hds1) - 1:
            tokens.append("[SEP]")
            segment_ids.append(0)
        elif i == len(hds1) - 1:
            tokens.append("[SEP]")
            segment_ids.append(1)
        else:
            raise EnvironmentError

    return tokens, segment_ids, i_sql_vocab, i_nlu, i_hds


def sort_pr_wc(pr_wc, g_wc):
    """
    Input: list
    pr_wc = [B, n_conds]
    g_wc = [B, n_conds]


    Return: list
    pr_wc_sorted = [B, n_conds]
    """
    pr_wc_sorted = []
    for b, pr_wc1 in enumerate(pr_wc):
        g_wc1 = g_wc[b]
        pr_wc1_sorted = []

        if set(g_wc1) == set(pr_wc1):
            pr_wc1_sorted = deepcopy(g_wc1)
        else:
            # no sorting when g_wc1 and pr_wc1 are different.
            pr_wc1_sorted = deepcopy(pr_wc1)

        pr_wc_sorted.append(pr_wc1_sorted)
    return pr_wc_sorted


cn_sum = {
    '〇': '0', '一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '零': '0',
    '壹': '1', '贰': '2', '叁': '3', '肆': '4', '伍': '5', '陆': '6', '柒': '7', '捌': '8', '玖': '9', '貮': '2', '两': '2',
}

cn_unit = {
    '十': 10,
    '拾': 10,
    '百': 100,
    '佰': 100,
    '千': 1000,
    '仟': 1000,
    '万': 10000,
    '萬': 10000,
    '亿': 100000000,
    '億': 100000000,
    '兆': 1000000000000,
    '角': 0.1,
    '分': 0.01
}


def chn_to_sum(chn):
    # 传入字符串
    sum = 0
    lis = []
    flo = False
    str_flo = ''
    for i in chn:
        if flo:
            if i in cn_sum:
                str_flo += cn_sum[i]
            if i in cn_unit:
                lis.append(cn_unit[i])
        else:
            if i == '点':
                flo = True
            if i in cn_sum:
                lis.append(cn_sum[i])
            if i in cn_unit:
                lis.append(cn_unit[i])
    for k in range(len(lis)):
        if k == len(lis) - 1:
            if str_flo:
                sum += float('.' + str_flo)
            if type(lis[k]) == str:
                sum = sum + int(lis[k])
        if type(lis[k]) in [int, float]:
            if lis[k] > sum:
                sum = (sum + int(lis[k - 1])) * lis[k]
            else:
                sum = sum + (int(lis[k - 1]) * lis[k])

    return round(sum, 2)
