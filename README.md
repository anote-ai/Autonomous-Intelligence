# Autonomous Intelligence

Autonomous Intelligence is an open-source research project by [Anote](https://anote.ai/) that enables collaborative multi-agent AI systems. The framework provides the infrastructure to create, deploy, and coordinate specialized AI agents that can operate both independently and together in dynamic environments. Agents communicate through defined pathways while an orchestrator manages task distribution, ensuring efficient execution and seamless collaboration. This architecture allows the system to adapt to changing conditions, automatically selecting the best agents, tools, and workflows to tackle complex problems. To learn more, see the video demo below:

[![Watch the video](https://img.youtube.com/vi/Nf-pc4xyTBI/0.jpg)](https://www.youtube.com/watch?v=Nf-pc4xyTBI)


### Core Components

| Component                    | Description                                                                                       |
|------------------------------|---------------------------------------------------------------------------------------------------|
| **Orchestrator**             | Central hub for task assignment, execution, and monitoring. Manages agent interactions and refines workflows dynamically. |
| **Agent**                    | An autonomous unit programmed to perform tasks, make decisions, and communicate with other agents. |
| **Task**                     | A specific assignment completed by an agent, providing all necessary details like description, tools, and responsibilities. |
| **Crew**                     | A collaborative group of agents working together to achieve a set of tasks. Crews define strategies for task execution and agent collaboration. |
| **Workflows**  | Frameworks for agent collaboration. This includes sequential tasks that are executed in an orderly progression, or hierarchical tasks are managed via a structured chain of command|
| **Models** | Backbone of intelligent agents, enabling capabilities like natural language understanding and reasoning. Includes models like GPT, Claude, Mistral, Gemini, and Llama that are Optimized for complex workflows. |
| **Tools**                     | A skill or function agents use to perform actions, that includes capabilities like search, computer use, data extraction, file uploading and advanced interactions. |

### Use Cases

Within the [Agent Registry](https://anote.ai/community/agents), we have added many domain specific agents. Here are a few example use cases:

| **Use Case**              | **Description**                                                                  | **Link**                                              |
|---------------------------|----------------------------------------------------------------------------------|------------------------------------------------------|
| **AI Assisted Coding**    | Automate feature implementations and pull requests                              | [Watch Video](https://www.youtube.com/watch?v=K2KUVdZjZnc) |
| **AI Assisted RFPs**      | Draft, refine, and submit grant proposals efficiently                           | [Watch Video](https://www.youtube.com/watch?v=fE4_Yjjfl0M) |
| **AI Assisted Outreach**  | Automate email campaigns, sequences, and follow-ups                             | [Learn More](https://upreach.ai/)                    |
| **Job Applications**      | Automate resume customization and job application submissions                   | [Learn More](https://roboapply.ai/)                  |

### Example Use Case: AI Assisted Outreach

1. **Input Query**: The user provides a task, e.g., “Reach out to a list of 10,000 New York-based heads of AI who work in mid-sized finance companies.”
2. **Data Collection**: The orchestrator leverages an AI-powered data foundation and the web to source the most reliable leads. The agent processes the input criteria to generate a list, such as Job Title: Data Scientist, Industry: Technology, Company Size: >1,000, Location: United States
3. **Agent Workflow**: The AI workflow processes the input by applying specific rules and guidelines to filter the data. Agents collaborate to refine the lead list and create tailored email drafts for each contact.
4. **Email and List Generation**: The system outputs a curated list of leads, including contact information, along with tailored email content ready for automated delivery.
5. **Automation**: Emails are automatically sent to the generated list of leads. The system tracks progress, showing the number of emails sent and responses received daily.
6. **Feedback Loop**: User feedback is incorporated to improve the lead generation process, refine email drafts, or adjust selection criteria for future tasks.

![alt text](https://github.com/nv78/Autonomous-Intelligence/blob/main/materials/assets/ExampleNew.png?raw=true)

For a full example of this working end to end for this use case, please see [Anote's Upreach Product](https://anote.ai/upreach).

### Set Up

We provide the setup instructions in ```CODEBASE_SETUP.md```. For any questions or issues, please [join our slack community](https://join.slack.com/t/anote-ai/shared_invite/zt-2vdh1p5xt-KWvtBZEprhrCzU6wrRPwNA) or [contact us](mailto:nvidra@anote.ai).
