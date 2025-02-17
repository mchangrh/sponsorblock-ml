from huggingface_hub import hf_hub_download
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from shared import CustomTokens
from errors import ClassifierLoadError, ModelLoadError
from functools import lru_cache
import pickle
import os
from dataclasses import dataclass, field
from typing import Optional
import torch


@dataclass
class ModelArguments:
    """
    Arguments pertaining to which model/config/tokenizer we are going to fine-tune from.
    """

    model_name_or_path: str = field(
        default=None,
        # default='google/t5-v1_1-small',  # t5-small
        metadata={
            'help': 'Path to pretrained model or model identifier from huggingface.co/models'
        }
    )

    # config_name: Optional[str] = field( # TODO remove?
    #     default=None, metadata={'help': 'Pretrained config name or path if not the same as model_name'}
    # )
    # tokenizer_name: Optional[str] = field(
    #     default=None, metadata={
    #         'help': 'Pretrained tokenizer name or path if not the same as model_name'
    #     }
    # )
    cache_dir: Optional[str] = field(
        default='models',
        metadata={
            'help': 'Where to store the pretrained models downloaded from huggingface.co'
        },
    )
    use_fast_tokenizer: bool = field(  # TODO remove?
        default=True,
        metadata={
            'help': 'Whether to use one of the fast tokenizer (backed by the tokenizers library) or not.'
        },
    )
    model_revision: str = field(  # TODO remove?
        default='main',
        metadata={
            'help': 'The specific model version to use (can be a branch name, tag name or commit id).'
        },
    )
    use_auth_token: bool = field(
        default=False,
        metadata={
            'help': 'Will use the token generated when running `transformers-cli login` (necessary to use this script '
            'with private models).'
        },
    )
    resize_position_embeddings: Optional[bool] = field(
        default=None,
        metadata={
            'help': "Whether to automatically resize the position embeddings if `max_source_length` exceeds the model's position embeddings."
        },
    )


@lru_cache(maxsize=None)
def get_classifier_vectorizer(classifier_args):
    # Classifier
    classifier_path = os.path.join(
        classifier_args.classifier_dir, classifier_args.classifier_file)
    if not os.path.exists(classifier_path):
        hf_hub_download(repo_id=classifier_args.classifier_model,
                        filename=classifier_args.classifier_file,
                        cache_dir=classifier_args.classifier_dir,
                        force_filename=classifier_args.classifier_file,
                        )
    with open(classifier_path, 'rb') as fp:
        classifier = pickle.load(fp)

    # Vectorizer
    vectorizer_path = os.path.join(
        classifier_args.classifier_dir, classifier_args.vectorizer_file)
    if not os.path.exists(vectorizer_path):
        hf_hub_download(repo_id=classifier_args.classifier_model,
                        filename=classifier_args.vectorizer_file,
                        cache_dir=classifier_args.classifier_dir,
                        force_filename=classifier_args.vectorizer_file,
                        )
    with open(vectorizer_path, 'rb') as fp:
        vectorizer = pickle.load(fp)

    return classifier, vectorizer


@lru_cache(maxsize=None)
def get_model_tokenizer(model_name_or_path, cache_dir=None, no_cuda=False):
    if model_name_or_path is None:
        raise ModelLoadError('Invalid model_name_or_path.')

    # Load pretrained model and tokenizer
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_name_or_path, cache_dir=cache_dir)
    if not no_cuda:
        model.to('cuda' if torch.cuda.is_available() else 'cpu')

    tokenizer = AutoTokenizer.from_pretrained(
        model_name_or_path, cache_dir=cache_dir)

    # Ensure model and tokenizer contain the custom tokens
    CustomTokens.add_custom_tokens(tokenizer)
    model.resize_token_embeddings(len(tokenizer))

    # TODO find a way to adjust based on model's input size
    # print('tokenizer.model_max_length', tokenizer.model_max_length)

    return model, tokenizer
