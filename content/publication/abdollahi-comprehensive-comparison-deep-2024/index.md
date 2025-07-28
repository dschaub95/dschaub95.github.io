---
title: A Comprehensive Comparison of Deep Learning-Based Compound-Target Interaction
  Prediction Models to Unveil Guiding Design Principles
authors:
- Sina Abdollahi
- Darius P. Schaub
- Madalena Barroso
- Nora C. Laubach
- Wiebke Hutwelker
- Ulf Panzer
- S.øren W. Gersting
- Stefan Bonn
date: '2024-10-28'
publishDate: '2025-07-28T11:54:38.977787Z'
publication_types:
- article-journal
doi: 10.1186/s13321-024-00913-1
abstract: The evaluation of compound-target interactions (CTIs) is at the heart of
  drug discovery efforts. Given the substantial time and monetary costs of classical
  experimental screening, significant efforts have been dedicated to develop deep
  learning-based models that can accurately predict CTIs. A comprehensive comparison
  of these models on a large, curated CTI dataset is, however, still lacking. Here,
  we perform an in-depth comparison of 12 state-of-the-art deep learning architectures
  that use different protein and compound representations. The models were selected
  for their reported performance and architectures. To reliably compare model performance,
  we curated over 300 thousand binding and non-binding CTIs and established several
  gold-standard datasets of varying size and information. Based on our findings, DeepConv-DTI
  consistently outperforms other models in CTI prediction performance across the majority
  of datasets. It achieves an MCC of 0.6 or higher for most of the datasets and is
  one of the fastest models in training and inference. These results indicate that
  utilizing convolutional-based windows as in DeepConv-DTI to traverse trainable embeddings
  is a highly effective approach for capturing informative protein features. We also
  observed that physicochemical embeddings of targets increased model performance.
  We therefore modified DeepConv-DTI to include normalized physicochemical properties,
  which resulted in the overall best performing model Phys-DeepConv-DTI. This work
  highlights how the systematic evaluation of input features of compounds and targets,
  as well as their corresponding neural network architectures, can serve as a roadmap
  for the future development of improved CTI models.
tags:
- Artificial Intelligence
- Deep learning
- Drug embeddings
- Drug-target interaction prediction
- Gold-standard datasets
- Mutated targets
- Protein descriptors
- Protein trainable embeddings
links:
- name: URL
  url: https://doi.org/10.1186/s13321-024-00913-1
---
