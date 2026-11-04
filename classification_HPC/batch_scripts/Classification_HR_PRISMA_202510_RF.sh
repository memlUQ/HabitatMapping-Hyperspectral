#!/bin/bash --login
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=MEMORY_REQUIRED
#SBATCH --job-name=class_HR_PRISMA_202510_RF
#SBATCH --time=HH:MN:SS
#SBATCH --partition=PARTITION
#SBATCH --account=ACCOUNT
#SBATCH -o slurmClass_HR_PRISMA_202510_RF.output
#SBATCH -e slurmClass_HR_PRISMA_202510_RF.error

cd /path/to/working/directory

module load anaconda3/2022.05

source $EBROOTANACONDA3/etc/profile.d/conda.sh

conda activate classification

python3 03_Classification.py 202510 Heron HR PRISMA 1000 RF