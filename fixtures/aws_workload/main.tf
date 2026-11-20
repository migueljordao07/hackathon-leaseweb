terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

variable "project_name" {
  description = "Synthetic demo workload name"
  type        = string
  default     = "skyshift-demo"
}

variable "instance_type" {
  description = "Synthetic compute size for demo workload"
  type        = string
  default     = "t3.micro"
}

variable "ami_id" {
  description = "Synthetic placeholder AMI identifier"
  type        = string
  default     = "ami-00000000000000000"
}

variable "bucket_name" {
  description = "Synthetic S3 bucket name for demo objects"
  type        = string
  default     = "skyshift-demo-workload-bucket"
}

resource "aws_s3_bucket" "demo" {
  bucket = var.bucket_name

  tags = {
    Name      = "${var.project_name}-bucket"
    Synthetic = "true"
  }
}

resource "aws_security_group" "app" {
  name        = "${var.project_name}-sg"
  description = "Synthetic security group for SkyShift demo workload"

  ingress {
    description = "HTTPS synthetic test traffic"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["192.0.2.0/24"]
  }

  egress {
    description = "Outbound synthetic traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["192.0.2.0/24"]
  }

  tags = {
    Name      = "${var.project_name}-sg"
    Synthetic = "true"
  }
}

resource "aws_instance" "app" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.app.id]

  tags = {
    Name      = "${var.project_name}-app"
    Bucket    = aws_s3_bucket.demo.bucket
    Synthetic = "true"
  }
}
