# ❓ Frequently Asked Questions (FAQ)

## **1. 📘 About Hasura**

### **What is Hasura?**
Hasura is a platform that provides a semantic data access layer. It simplifies data integration and access, enabling rapid development and seamless scaling of applications.

### **How quickly can you set Hasura up?**
A supergraph can be created and online in Hasura Cloud in a matter of seconds from first downloading the DDN toolkit locally.

### **What are supergraphs and subgraphs?**
Hasura’s architecture uses [supergraphs](https://hasura.io/docs/3.0/support/glossary#supergraph) and [subgraphs](https://hasura.io/docs/3.0/support/glossary#subgraphs) to organize metadata into logical, self-contained sections. The subgraph maps to the data domain and the supergraph federates data domains into an organisation-wide semantic data access layer.

### **What are Data Connectors?**
Subgraphs utilize [data connectors](https://hasura.io/docs/3.0/support/glossary#native-data-connectors) to interface with various data sources. Connectors are separate from the Hasura Engine and can be [custom-built](https://hasura.io/docs/3.0/connectors/build-your-own/).

### **How can I Configure Subgraphs**
Subgraphs manage [data types](https://hasura.io/docs/3.0/supergraph-modeling/types), [data models](https://hasura.io/docs/3.0/supergraph-modeling/models), [commands](https://hasura.io/docs/3.0/supergraph-modeling/commands), [permissions](https://hasura.io/docs/3.0/supergraph-modeling/permissions), and [relationships](https://hasura.io/docs/3.0/supergraph-modeling/relationships).


## **2. 🌟 Getting Started**

### **How do I begin with Hasura?**
Start with our [Quickstart Guide](https://hasura.io/docs/3.0/getting-started/quickstart/) to set up your Hasura environment and connect to your databases.

### **What are the prerequisites?**
* Locally, you’ll need docker and the Hasura DDN client installed
* In our cloud, we'll run Hasura for you
* Using your cloud for a data plane will require k8s knowledge

## **3. 🛠️ Configuration and Integration**

### **Can Hasura integrate with multiple databases?**
Yes, Hasura supports integration with multiple databases and can federate data across different sources into a single data access layer.

## **4. 📧 Support and Troubleshooting**

### **What if I encounter issues?**
Your first port of call will be found on the team page in this wiki. For further assistance, contact our support team or access our [Enterprise Support](mailto:support@hasura.io).

### **How do I report a problem or request support?**
Report issues via our [GitHub issues page](https://github.com/hasura/v3-engine/issues) or email our [support team](mailto:support@hasura.io). Enterprise customers should contact their account manager for dedicated support.

## **5. 📚 Community**

### **How can my team get involved with Hasura?**
We encourage as many team members as possible to get involved in the community. Invite them into this space for us to all collaborate and send out links to the demo projects for them to test Hasura with real data in real environments.

### **How do I stay up to date on changes**
The changelog in this wiki will give you a view of the changes to this project. We'd also recommend joining us for our next call to discuss the latest updates, share feedback, and connect with fellow Hasura users
