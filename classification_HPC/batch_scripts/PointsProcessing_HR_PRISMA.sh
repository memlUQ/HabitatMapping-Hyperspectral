#!/bin/bash --login
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=MEMORY_REQUIRED
#SBATCH --job-name=points_proc_HR_PRISMA_202411
#SBATCH --time=HH:MN:SS
#SBATCH --partition=PARTITION
#SBATCH --account=ACCOUNT
#SBATCH -o slurmPointsProc_HR_PRISMA_202411.output
#SBATCH -e slurmPointsProc_HR_PRISMA_202411.error

cd /path/to/working/directory

module load anaconda3/2022.05

source $EBROOTANACONDA3/etc/profile.d/conda.sh

conda activate points_processing

python3 02_PointsProcessing.py 202411 Heron HR PRISMA 1000