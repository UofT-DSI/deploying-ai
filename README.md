# Deploying AI

## Content
* [Description](#description)
* [Learning Outcomes](#learning-outcomes)
* [Contacts](#contacts)
* [Delivery of the Learning module](#delivery-of-the-learning-module)
* [Schedule](#schedule)
* [Requirements](#requirements)
* [Assessment](#assessment)
  + [Quizzes](#quizzes)
  + [Assignments](#assignments)
* [Requirements](#requirements)
* [Resources](#resources)
  + [Documents](#documents)
  + [Videos](#videos)
* [Folder Structure](#folder-structure)



## Description

This microcredential provides an overview of the Design of AI systems that are embedded in data products and applications. It covers the fundamental components of the infrastructure, systems, and methods necessary to implement and maintain AI systems. 

The course has two components: 

+ A discussion of the main issues and challenges faced in production, together with some approaches to address them.
+ A live lab with demonstrations of implementation techniques. 

The course is based on [Chip Huyen's book, AI Engineering](https://huyenchip.com/books/). We will cover the following areas:

+ **Part 1. Fundamentals.** The first part of the course will be devoted to building fundamental knowledge about AI models. We explore their evolution from Machine Learning systems and highlight the differences between Machine Learning and the Foundation Models that underpin most AI applications. 

  - **Introduction to AI Systems**
    
    * What is an AI System?
    * Use cases and planning an AI application
    * The AI engineering Stack

  - **An overview of Foundation Models**
    
    * From machine learning to foundation models via deep learning
    * Model architectures
    * Training, pre-training, post-training models
    * Sampling, hallucinations, and the probabilistic nature of AI
  
  - **Model Evaluation and System Evaluation**
  
    * Performance metrics
    * Exact evaluation and using AI as a judge
    * Designing an evaluation pipeline

+ **Part 2. Working with AI Systems.** Foundation models are expensive and, most of the time, are impractical to train by organizations and users. In current engineering practice, most AI applications are built on pre-trained models. This portion of the course will cover the main techniques to build AI applications and systems.

  - **Prompt Engineering**

    * System vs user prompt, context length and context efficiency
    * Prompt engineering best practices
    * Defensive prompt engineering

  - **Retrieval Augmented Generation (RAG)**

    * RAG Architecture
    * Retrieval Algorithms and optimization

  - **Agents**

    * Planning
    * Interacting with APIs and MCP
    * Agent failure modes and evaluation

- **Part 3. Optimization and System Design.** Enhancing AI systems can be achieved by finetuning them on specific tasks or to provide outputs that avoid undesired results. As well, good design practices can be used to reduce latency and costs and to provide consistent experiences for users.

  - **Finetuning**

    * Finetuning overview
    * Finetuning techniques

  - **Data Engineering**

    * Data curation
    * Data augmentation and synthesis
    * Data processing

  - **Optimization and System Design**

    * Inference optimization
    * AI engineering architecture
    * User feedback

We will discuss the tools and techniques required to do the above in good order and at scale. However, we will not discuss the inner workings of models, advantages, and so on. We will also not discuss the theoretical aspects of feature engineering or hyperparameter tuning. We will focus on tools and reproducibility.

## Learning Outcomes

By the end of this module, participants will be able to:

+ Define foundation models and describe the main characteristics of AI systems that are based on foundation models. Explain how AI systems differ from other systems based on Machine Learning.
+ Describe the main components of an AI system architecture.
+ Explain the primary methods to enhance the performance and security of AI systems, including prompt engineering, fine-tuning, and retrieval augmented generation.
+ Contrast and evaluate different approaches to implementing foundation models.
+ Implement data flows and processes to automate tasks using foundation models, including conversational interfaces, agents, and retrieval augmented generation, among others.


## Contacts

### Deploying AI (April 14 - April 30)

**Questions can be submitted to the _help_ channel on Slack**

* Technical Facilitator: 
  * [Rogelio Cuevas](https://www.linkedin.com/in/jcalderon/)
  
* Learning Support: 
  * [Dmytro Bonislavskyi](https://www.linkedin.com/in/dmytro-bonislavskyi/)
  * [Nakul Upadhya](https://www.linkedin.com/in/nakulupadhya/)
  

## Delivery of the Learning Module

This module will include live learning sessions and optional, asynchronous work periods. During live learning sessions, the Technical Facilitator will introduce and explain key concepts and demonstrate core skills. Learning is facilitated during this time. Before and after each live learning session, the instructional team will be available to answer questions about the module's core concepts. Optional work periods are to be used to seek help from peers, the Learning Support team, and to work through the homework and assignments in the learning module, with access to live help. Content is not facilitated, but rather, this time should be driven by participants. We encourage participants to come to these work periods with questions and problems to work through. 
 
Participants are encouraged to engage actively during the learning module. The key to developing the core skills in each learning module is through practice. The more participants engage in coding alongside the instructional team and apply these skills in each module, the more likely they are to solidify them. 

# Schedule

## Deploying AI (April 14 - April 30)

|Type |Date        |Topic                             |
|-----|------------|----------------------------------|
|Live| Apr. 14 | Introduction to AI Engineering|
|Live| Apr. 15 | Introduction to Foundation Models |
|Live| Apr. 16 | Evaluating Foundation Models |
|Work| Apr. 17 | Work Period |
|Deadline| Apr. 20 | Assignment 1 Due |
|Live| Apr. 21 | Prompt Engineering |
|Live| Apr. 22 | Retrieval Augmented Generation |
|Live| Apr. 23 | Agents |
|Work| Apr. 24 | Work Period |
|Deadline| Apr. 27 | Assignment 2 Due |
|Live| Apr. 29 | Case Study |
|Live| Apr. 28 | Fine Tuning |
|Live| Apr. 30 | Dataset Engineering |
|Work| May. 1 | Work Period |


### Requirements
* Participants are not expected to have any coding experience; the learning content has been designed for beginners.
* Participants are encouraged to ask questions, and collaborate with others to enhance their learning experience.
* Participants must have a computer and an internet connection to participate in online activities.
* Participants must not use generative AI such as ChatGPT to generate code to complete assignments. It should be used as a support tool to help you find answers to questions you may have.
* We expect participants to have completed the instructions mentioned in the [onboarding repo](https://github.com/UofT-DSI/onboarding/blob/main/environment_setup/README.md).
* We encourage participants to default to having their camera on at all times, and turning the camera off only as needed. This will significantly enhance the learning experience for all participants and provide real-time feedback for the instructional team. 


### Assessment

Your performance on this module will be assessed using six quizzes and two assignments. 

#### Quizzes

Quizzes will help you build key concepts in foundation models and AI Engineering. In our experience, learners take 5-10 minutes to complete each quiz, achieving an average score of 80%. 

+ Each quiz will contain material from each live learning session.
+ You will receive a link to each quiz during the respective live learning session. The links are personalized; please do not share them. If you did not receive a link, contact any member of the course delivery team.
+ Each quiz will contain about 10 questions of different types: true/false, multiple choice, simple selection, etc.
+ All quizzes are mandatory and should be submitted by their due date. 
+ The quizzes will remain open until their respective due dates, after which you will not have access to them.

#### Assignments

Assignments will help you develop coding and debugging skills. They will cover foundational skills and will extend to advanced concepts. We recommend that you attempt all assignments and submit your work, even if it is incomplete (partial submissions will earn partial marks). 

+ Each assignment should be submitted using the usual method in DSI via a Pull Request. 
+ The assignments and their respective rubrics are:

  

#### Grades

All participants will receive a pass or fail mark. The mark will be determined as follows:

+ Quizzes' average score - 60%
+ Assignment 1 - 20%
+ Assignment 2 - 20%

Assignments' assessment can be transformed into a numeric grade using:

+ Complete - 100 points
+ Incomplete / Partially Complete - 50 points
+ Missing / Not submitted - 0 points

For this course, 60 points are required to receive a "pass" mark.

For example, a learner with the following grades would receive "pass":

+ Quizzes 80
+ Assignment 1 - Complete (100)
+ Assignment 2 - Incomplete (50)
+ (0.6 * 80) + (0.2 * 100) + (0.2 * 50) = 48 + 20 + 10 = 78 > 60

A different learner with grades as shown below would receive "fail":

+ Quizzes 80
+ Assignment 1 - Incomplete (50)
+ Assignment 2 - Missing (0)
+ (0.6 * 80) + (0.2 * 50) + 0 = 48 + 10 + 0 = 58 < 60

## Resources

### Python

+ [Python 101](https://python101.pythonlibrary.org/), by Mike Driscoll

### uv

+ uv's [documentation page](https://docs.astral.sh/uv/)

  - [Installation instructions](https://docs.astral.sh/uv/getting-started/installation/) for most popular operating systems. 
  - [First steps](https://docs.astral.sh/uv/getting-started/first-steps/) after installing uv
  - [Features](https://docs.astral.sh/uv/getting-started/features/)

+ [Managing Python Projects With uv: An All-in-One Solution](https://realpython.com/python-uv/), by Real Python



### Docker

+ [Getting Started](https://www.docker.com/get-started/) with Docker
+ Installation instructions:

  - [Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
  - [Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
  - [Linux](https://docs.docker.com/desktop/setup/install/linux/)
+ Docker Desktop [Documnetation](https://docs.docker.com/desktop/)
+ [What is Docker?](https://www.youtube.com/watch?v=Gjnup-PuquQ) on Youtube
+ A [playlist with tutorials about Docker](https://www.youtube.com/playlist?list=PLe4mIUXfbIqaYmsoFahYCbijPU4rjM38h) on YouTube

### Tools and API

+ [OpenAI Documentation](https://platform.openai.com/docs/concepts)
+ [OpenAI Platform](https://platform.openai.com/)
+ [OpenAI Cookbook](https://cookbook.openai.com/)
+ [LangChain](https://www.langchain.com/)



## Folder Structure

```markdown
.
├── .github
├── 01_materials
├── 02_activities
├── 03_instructional_team
├── 04_this_cohort
├── 05_src
├── .gitignore
├── LICENSE
├── SETUP.md
├── pyproject.toml
└── README.md
```

* **.github**: Contains issue templates and pull request templates for the repository.
* **materials/slides**: Module slides and interactive notebooks (.ipynb files) used during learning sessions.
* **activities**: Contains graded assignments, exercises, and homework to practice concepts covered in the learning module.
* **instructional_team**: Resources for the instructional team.
* **this_cohort**: Additional materials and resources for this cohort, including live coding files.
* **src/data**: Source code, databases, logs, and required dependencies (requirements.txt) needed during the module.
* **.gitignore**: Files to exclude from this folder, specified by the Technical Facilitator
* **LICENSE**: The license for this repository.
* **SETUP.md**: Contains the steps required to set up this repo for the module.
* **pyproject.toml**: Tells Python which packages this repo needs to run.  
* **README.md**: This file.
