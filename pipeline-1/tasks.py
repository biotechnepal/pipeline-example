import time
import datetime
import os
import sys
import subprocess
import yaml


class Result(object):
    def __init__(self, infiles, outfiles, log=None, stdout=None, stderr=None,
                 desc=None, failed=False, cmds=None):
        if isinstance(infiles, basestring):
            infiles = [infiles]
        if isinstance(outfiles, basestring):
            outfiles = [outfiles]
        self.infiles = infiles
        self.outfiles = outfiles
        self.log = log
        self.stdout = stdout
        self.stderr = stderr
        self.elapsed = None
        self.failed = failed
        self.desc = desc
        self.cmds = cmds

    def report(self, logger_proxy, logging_mutex):
        """
        Prints a nice report
        """
        with logging_mutex:
            if not self.desc:
                self.desc = ""
            logger_proxy.info(' Task: %s' % self.desc)
            logger_proxy.info('     Time: %s' % datetime.datetime.now())
            if self.cmds is not None:
                logger_proxy.debug('     Commands: %s' % str(self.cmds))
            for output_fn in self.outfiles:
                output_fn = os.path.normpath(os.path.relpath(output_fn))
                logger_proxy.info('     Output:   %s' % output_fn)
            if self.log is not None:
                logger_proxy.info('     Log:      %s' % self.log)
            if self.failed:
                logger_proxy.error('=' * 80)
                logger_proxy.error('Error in %s' % self.desc)
                if self.cmds:
                    logger_proxy.error(str(self.cmds))
                if self.stderr:
                    logger_proxy.error('====STDERR====')
                    logger_proxy.error(self.stderr)
                if self.stdout:
                    logger_proxy.error('====STDOUT====')
                    logger_proxy.error(self.stdout)
                if self.log is not None:
                    logger_proxy.error('   Log: %s' % self.log)
                logger_proxy.error('=' * 80)
                sys.exit(1)
            logger_proxy.info('')

def fastq_to_other_files(config, extension):
    """
    generates input/output files for each sample
    `extension`.  This is the primary mapping to go from fastq to analyzed
    data.

    output dirs are also created if necessary.

    extension can be a list

    """
    if isinstance(extension, basestring):
        extension = [extension]
    for sample in config['samples']:
        infile = sample['fastq']
        outdir = os.path.join(config['output dir'], sample['label'])
        if not os.path.exists(outdir):
            os.system('mkdir -p %s' % outdir)
        stub = os.path.join(outdir, sample['label'])
        outfiles = []
        for ext in extension:
            # add dot if needed
            if ext[0] != '.':
                ext = '.' + ext
            outfiles.append(stub + ext)
        if len(outfiles) == 1:
            outfiles = outfiles[0]
        yield infile, outfiles


def bowtie(fastq, outfile, config):
    """
    Use bowtie to map `fastq`, saving the SAM file as `outfile`.  Ensures that
    '--sam' is in the parameters.
    """
    index = config['index']
    params = config['bowtie params'].split()
    if ('--sam' not in params) and ('-S' not in params):
        params.append('-S')

    cmds = ['bowtie']
    cmds.extend(params)
    cmds.append(index)
    cmds.append(fastq)
    print outfile
    logfn = outfile + '.log'
    p = subprocess.Popen(
            cmds, stdout=open(outfile, 'w'), stderr=open(logfn, 'w'),
            bufsize=1)
    stdout, stderr = p.communicate()
    return Result(
            infiles=fastq, outfiles=outfile, cmds=' '.join(cmds), log=logfn)


def count(samfile, countfile, config):
    cmds = ['htseq-count']
    cmds += config['htseq params'].split()
    cmds += [samfile,
            config['gff']]
    p = subprocess.Popen(
            cmds, stdout=open(countfile, 'w'),
            stderr=subprocess.PIPE, bufsize=1)
    stdout, stderr = p.communicate()
    failed = p.returncode
    return Result(
            infiles=samfile,
            outfiles=countfile,
            stderr=stderr,
            failed=failed,
            cmds=' '.join(cmds))
