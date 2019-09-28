from labeler.labelers.single_file import SingleFileLabeler


class GridLabeler(SingleFileLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 show_notes=True,
                 num_items=10):
        template_args = {'show_notes': show_notes}
        super().__init__(root=root,
                         labels_csv=labels_csv,
                         extensions=('.gif'),
                         output_dir=output_dir,
                         template='label_grid_images.html',
                         template_extra_args=template_args,
                         num_items=num_items)
