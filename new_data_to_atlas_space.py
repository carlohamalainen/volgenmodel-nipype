#!/usr/bin/env python3
from os.path import join as opj
import os
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink, DataGrabber
from nipype.pipeline.engine import Workflow, Node, MapNode
from nipype.interfaces.minc import  \
        Resample,       \
        BigAverage,     \
        VolSymm
import argparse

def create_workflow(
        xfm_dir,
        xfm_pattern,
        atlas_dir,
        atlas_pattern,
        source_dir,
        source_pattern,
        work_dir,
        out_dir,
        name="new_data_to_atlas_space"
):
        wf = Workflow(name=name)
        wf.base_dir = opj(work_dir)

        datasource_source = Node(
                interface=DataGrabber(
                        sort_filelist=True
                ),
                name='datasource_source'
        )
        datasource_source.inputs.base_directory = os.path.abspath(source_dir)
        datasource_source.inputs.template = source_pattern

        datasource_xfm = Node(
                interface=DataGrabber(
                        sort_filelist=True
                ),
                name='datasource_xfm'
        )
        datasource_xfm.inputs.base_directory = os.path.abspath(xfm_dir)
        datasource_xfm.inputs.template = xfm_pattern

        datasource_atlas = Node(
                interface=DataGrabber(
                        sort_filelist=True
                ),
                name='datasource_atlas'
        )
        datasource_atlas.inputs.base_directory = os.path.abspath(atlas_dir)
        datasource_atlas.inputs.template = atlas_pattern

        resample = MapNode(
                interface=Resample(
                        sinc_interpolation=True
                ),
                name='resample_',
                iterfield=['input_file', 'transformation']
        )
        wf.connect(datasource_source, 'outfiles', resample, 'input_file')
        wf.connect(datasource_xfm, 'outfiles', resample, 'transformation')
        wf.connect(datasource_atlas, 'outfiles', resample, 'like')

        bigaverage = Node(
                interface=BigAverage(
                        output_float=True,
                        robust=False
                ),
                name='bigaverage',
                iterfield=['input_file']
        )

        wf.connect(resample, 'output_file', bigaverage, 'input_files')

        datasink = Node(
                interface=DataSink(
                        base_directory=out_dir,
                        container=out_dir
                ),
                name='datasink'
        )

        wf.connect([(bigaverage, datasink, [('output_file', 'average')])])
        wf.connect([(resample, datasink, [('output_file', 'atlas_space')])])
        wf.connect([(datasource_xfm, datasink, [('outfiles', 'transforms')])])
        
        return wf

if __name__ == "__main__":
        parser = argparse.ArgumentParser()

        parser.add_argument(
                "--name",
                type=str,
                required=True
        )

        parser.add_argument(
                "--xfm_dir",
                type=str,
                required=True
        )

        parser.add_argument(
                "--xfm_pattern",
                type=str,
                required=True
        )

        parser.add_argument(
                "--source_dir",
                type=str,
                required=True
        )

        parser.add_argument(
                "--source_pattern",
                type=str,
                required=True
        )

        parser.add_argument(
                "--atlas_dir",
                type=str,
                required=True
        )

        parser.add_argument(
                "--atlas_pattern",
                type=str,
                required=True
        )

        parser.add_argument(
                "--work_dir",
                type=str,
                required=True
        )

        parser.add_argument(
                "--out_dir",
                type=str,
                required=True
        )

        args = parser.parse_args()

        wf = create_workflow(
                xfm_dir=args.xfm_dir,
                xfm_pattern=args.xfm_pattern,
                atlas_dir=args.atlas_dir,
                atlas_pattern=args.atlas_pattern,
                source_dir=args.source_dir,
                source_pattern=args.source_pattern,
                work_dir=args.work_dir,
                out_dir=args.out_dir,
                name=args.name
        )

        wf.run(
                plugin='MultiProc',
                plugin_args={
                        'n_procs': int(
                                os.environ["NCPUS"] if "NCPUS" in os.environ else os.cpu_count
                        )
                }
        )
