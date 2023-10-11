import random
import re
import uuid
from typing import Optional

from slashgpt.chat_config import ChatConfig
from slashgpt.chat_context import ChatContext
from slashgpt.dbs.db_pinecone import DBPinecone
from slashgpt.dbs.vector_engine_openai import VectorEngineOpenAI
from slashgpt.function.jupyter_runtime import PythonRuntime
from slashgpt.history.storage.abstract import ChatHistoryAbstractStorage
from slashgpt.history.storage.memory import ChatHistoryMemoryStorage
from slashgpt.llms.model import LlmModel
from slashgpt.manifest import Manifest
from slashgpt.utils.print import print_debug, print_error, print_info, print_warning


class ChatSession:
    """It represents a chat session with a particular AI agent."""

    def __init__(
        self,
        config: ChatConfig,
        default_llm_model: LlmModel = None,
        user_id: Optional[str] = None,
        history_engine: ChatHistoryAbstractStorage = None,
        manifest={},
        agent_name: str = "GPT",
        intro: bool = True,
        restore: bool = False,
        memory: Optional[dict] = None,
    ):
        """
        Args:

            config (ChatConfig or its subclass): Chat configuration (LLM models and engines)
            default_llm_model (LlmModel, optional): Default LLM model
            user_id (str, optional): User Id (for history)
            history_engine (ChatHistoryAbstractStorage, optional): Histroy engine
            agent_name (str, optional): Display name of agent
            intro (bool, optional): True if the introduction message should be appended.
            restore (bool, optional): True if we are restoring an existing session.
            memory (dict, optional): The initial value of short term memory
        """
        self.config = config
        """Configuration Object (ChatConfig), which specifies accessible LLM models"""
        self.agent_name = agent_name
        """Display name of the AI agent (str)"""
        self.manifest = Manifest(manifest if manifest else {}, config.base_path, agent_name)
        """Manifest which specifies the behavior of the AI agent (Manifest)"""
        self.user_id = user_id if user_id else str(uuid.uuid4())
        """Specified user id or randomly generated uuid (str)"""
        self.context = ChatContext(history_engine or ChatHistoryMemoryStorage(self.user_id, agent_name))
        """Chat history (ChatContext)"""

        # Load the model name and make it sure that we have required keys
        if self.manifest.model():
            llm_model = self.config.get_llm_model_from_manifest(self.manifest)
        else:
            if default_llm_model:
                llm_model = default_llm_model
            else:
                llm_model = self.config.get_default_llm_model()
        self.set_llm_model(llm_model)

        # Load the prompt, fill variables and append it as the system message
        self.context.setMemory(memory or {})
        self.prompt = self.manifest.prompt_data(config.manifests if hasattr(config, "manifests") else {}, memory)
        """Prompt for the AI agent (str)"""

        if self.prompt and not restore:
            self.append_message("system", self.prompt, True)

        # Prepare embedded database index
        self.vector_db = self.__get_vector_db()
        """Associated vector database (DBPinecone, optional, to be virtualized)"""

        # Load functions file if it is specified
        self.functions = self.manifest.functions()
        """List of function definitions (list, optional)"""
        if self.functions and self.config.verbose:
            print_debug(self.functions)

        self.intro_message = self.__set_intro(intro)
        """Introduction message (str, optional)"""

    def set_llm_model(self, llm_model: LlmModel):
        """Set the LLM model"""
        if llm_model.check_api_key():
            self.llm_model = llm_model
        else:
            print_error("You need to set " + llm_model.get("api_key") + " to use this model. ")
        if self.config.verbose:
            print_debug(f"Model = {self.llm_model.name()}")

    def __get_vector_db(self):
        # Todo: support other vector db and vector engine
        embeddings = self.manifest.get("embeddings")
        if embeddings:
            table_name = embeddings.get("name")
            try:
                if embeddings["db_type"] == "pinecone":
                    return DBPinecone.factory(table_name, VectorEngineOpenAI, self.config.verbose)
            except Exception as e:
                print_warning(f"Pinecone Error: {e}")

    """
    Append a message to the chat session, specifying the role ("user", "system" or "function").
    In case of a function message, the name specifies the function name.
    """

    def append_message(self, role: str, message: str, preset: bool, name=None):
        """Append a message to the chat history
        Args:

            role (str): Either "user", "system" or "function"
            message (str): Message
            preset (bool): True, if it is preset by the manifest
            name (str, optional): function name (when the role is "function")
        """
        self.context.append_message({"role": role, "content": message, "name": name, "preset": preset})

    def append_user_question(self, message: str):
        """Append a question from the user to the history
        and update the prompt if necessary (e.g, RAG)"""
        self.append_message("user", message, False)
        if self.vector_db:
            articles = self.vector_db.fetch_related_articles(self.context.messages(), self.llm_model.name(), self.llm_model.max_token() - 500)
            assert self.context.get_message_prop(0, "role") == "system", "Missing system message"
            self.context.set_message(
                0,
                {
                    "role": "system",
                    "content": re.sub("\\{articles\\}", articles, self.prompt, 1),
                },
            )

    def __set_intro(self, use_intro: bool):
        intro_message = None
        intro = self.intro()
        if use_intro and intro:
            intro_message = intro[random.randrange(0, len(intro))]
            self.append_message("assistant", intro_message, True)
        return intro_message

    def call_llm(self):
        """
        Let the LLM generate a responce based on the messasges in this session.

        Returns:

            role (str): "assistent"
            res (str): message
            function_call (dict): json representing the function call (optional)
        """
        messages = self.context.messages()
        (role, res, function_call) = self.llm_model.generate_response(messages, self.manifest, self.config.verbose)

        if self.config.verbose and function_call is not None:
            print_info(function_call)

        if role and res:
            self.append_message(role, res, False)

        return (res, function_call)

    def temperature(self):
        """Temperature specified in the manifest"""
        return self.manifest.temperature()

    def intro(self):
        """Introduction messages specified in the manifest"""
        return self.manifest.get("intro")

    def username(self):
        """User name specified in the manifest"""
        return self.manifest.username()

    def botname(self):
        """Bot name specified in the manifest"""
        return self.manifest.botname()

    def title(self):
        """Title of the AI agent specified in the manifest"""
        return self.manifest.title()

    def call_loop(self, callback, verbose: bool = False, runtime: PythonRuntime = None):
        # Ask LLM to generate a response.
        (res, function_call) = self.call_llm()

        if res:
            callback("bot", res)

        if function_call:
            (action_data, action_method) = function_call.emit_data(verbose)
            if action_method:
                callback("emit", (action_method, action_data))
            else:
                (
                    function_message,
                    function_name,
                    should_call_llm,
                ) = function_call.process_function_call(
                    self.context,
                    runtime,
                    verbose,
                )
                if function_message:
                    callback("function", (function_name, function_message))

                if should_call_llm:
                    self.call_loop(callback, verbose, runtime)
