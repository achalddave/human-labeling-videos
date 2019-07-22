# Image labeler

# Example: Labeling ImageNet Video Frames

To label some sample images, first edit the `IMAGES_ROOT` variable in
`imagenetvid.cfg` to point to the root of your ImageNet Vid dataset.

```bash
FLASK_DEBUG=1 FLASK_APP=label.py FLASK_CONFIG=imagenetvid.cfg \
flask run -p 8000 -h 0.0.0.0
```

IGNORE BELOW FOR NOW; instructions below not updated from original video labeler
used by @achald for a different project.

# Filtering

Once videos are labeled, you can filter the results by using the
`filter_labels.py` script, like so:

```bash
python filter_labels.py \
    --input-labels <path-to-labels> \
    --must-have ${MUST_HAVE_LABELS} \
    --must-not-have ${MUST_NOT_HAVE_LABELS} \
    --output-labels <path-to-filtered-labels> \
    --labels-list <path-to-labels-list>
```

In general, the you should use the following setup:

perfect                 -
moving-unlabeled        - MUST NOT HAVE
static-labeled          - MUST NOT HAVE
no-moving-labeled       - MUST NOT HAVE
oversegmented-moving    - MUST NOT HAVE
static-part-labeled     - MUST NOT HAVE
interesting-video       -
look-again              - MUST NOT HAVE
challenging             -
always-moving           -

In a sense, the 'perfect' label is kind of redundant; it just implies that
moving-unlabeled, static-labeled, and no-moving-labeled are all false.
