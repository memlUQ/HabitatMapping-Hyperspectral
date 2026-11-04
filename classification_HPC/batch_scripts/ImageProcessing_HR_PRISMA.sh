#!/bin/bash --login
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=MEMORY_REQUIRED
#SBATCH --job-name=image_proc_HR_PRIMSA
#SBATCH --time=HH:MN:SS
#SBATCH --partition=PARTITION
#SBATCH --account=ACCOUNT
#SBATCH -o slurmImageProc_HR_PRISMA.output
#SBATCH -e slurmImageProc_HR_PRISMA.error

cd /path/to/working/directory

module load anaconda3/2022.05

source $EBROOTANACONDA3/etc/profile.d/conda.sh

conda activate image_processing

python3 01_ImageProcessing.py 202411 Heron HR PRISMA 1000 10000