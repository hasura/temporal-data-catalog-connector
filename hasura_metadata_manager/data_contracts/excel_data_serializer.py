from typing import Dict

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from .data_contract import DataContract
from .documentation_reference import DocumentationReference
from .person import Person
from ..object_type.field.object_field import ObjectField
from ..object_type.object_type import ObjectType


class ExcelDataSerializer:
    """
    Serializes data from a multi-sheet Excel workbook to database models.

    Expected Excel Workbook Structure:
    1. ObjectTypes Sheet
    2. ObjectFields Sheet
    3. Persons Sheet
    4. DataContracts Sheet
    5. DocumentationReferences Sheet
    """

    @classmethod
    def serialize_from_excel(cls, file_path: str, session: Session):
        """
        Main method to serialize an entire Excel workbook to database models.

        :param file_path: Path to the Excel file
        :param session: SQLAlchemy session
        """
        # Read the Excel file
        xls = pd.ExcelFile(file_path)

        # Serialize each sheet in a specific order
        persons = cls._serialize_persons(xls.parse('Persons'), session)
        object_types = cls._serialize_object_types(xls.parse('ObjectTypes'), session)
        data_contracts = cls._serialize_data_contracts(
            xls.parse('DataContracts'),
            object_types,
            persons,
            session
        )
        cls._serialize_documentation_references(
            xls.parse('DocumentationReferences'),
            data_contracts,
            session
        )

        # Commit the session
        session.commit()

    @classmethod
    def _serialize_persons(cls, df: pd.DataFrame, session: Session) -> Dict[str, Person]:
        """
        Serialize Persons from DataFrame

        :param df: DataFrame containing person data
        :param session: SQLAlchemy session
        :return: Dictionary of created/updated persons keyed by email
        """
        persons = {}
        for _, row in df.iterrows():
            # Convert NaN to None
            person_data = row.replace({np.nan: None}).to_dict()

            # Ensure string for areas of expertise
            if person_data.get('areasOfExpertise') and isinstance(person_data['areasOfExpertise'], str):
                person_data['areasOfExpertise'] = [
                    area.strip() for area in person_data['areasOfExpertise'].split(',')
                ]

            person = Person.from_json(person_data, session)
            persons[person.email] = person

        return persons

    @classmethod
    def _serialize_object_types(cls, df: pd.DataFrame, session: Session) -> Dict[str, ObjectType]:
        """
        Serialize ObjectTypes from DataFrame

        :param df: DataFrame containing object type data
        :param session: SQLAlchemy session
        :return: Dictionary of created/updated object types keyed by name
        """
        object_types = {}
        for _, row in df.iterrows():
            # Convert row to dictionary, replacing NaN with None
            object_type_data = row.replace({np.nan: None}).to_dict()

            # Prepare field mapping if exists
            if object_type_data.get('fieldMapping'):
                try:
                    object_type_data['fieldMapping'] = eval(object_type_data['fieldMapping'])
                except:
                    object_type_data['fieldMapping'] = {}

            # You'd need to pass a Subgraph instance here in a real implementation
            # For this example, we'll mock it
            from ..subgraph import Subgraph
            mock_subgraph = Subgraph(name=object_type_data.get('subgraphName', 'default_subgraph'))

            object_type = ObjectType.from_json(
                {
                    'kind': 'ObjectType',
                    'definition': object_type_data
                },
                mock_subgraph,
                session
            )
            object_types[object_type.name] = object_type

        return object_types

    @classmethod
    def _serialize_object_fields(
            cls,
            df: pd.DataFrame,
            object_types: Dict[str, ObjectType],
            session: Session
    ) -> Dict[str, ObjectField]:
        """
        Serialize ObjectFields from DataFrame

        :param df: DataFrame containing object field data
        :param object_types: Dictionary of existing object types
        :param session: SQLAlchemy session
        :return: Dictionary of created/updated object fields
        """
        object_fields = {}
        for _, row in df.iterrows():
            # Convert row to dictionary, replacing NaN with None
            field_data = row.replace({np.nan: None}).to_dict()

            # Get corresponding object type
            object_type_name = field_data.get('objectTypeName')
            object_type = object_types.get(object_type_name)

            if not object_type:
                print(f"Warning: No object type found for {object_type_name}")
                continue

            # Prepare type information
            if 'type' not in field_data:
                field_data['type'] = field_data.get('scalarTypeName', 'String')

            object_field = ObjectField.from_json(field_data, object_type, session)
            object_fields[f"{object_type_name}_{object_field.logical_field_name}"] = object_field

        return object_fields

    @classmethod
    def _serialize_data_contracts(
            cls,
            df: pd.DataFrame,
            object_types: Dict[str, ObjectType],
            persons: Dict[str, Person],
            session: Session
    ) -> Dict[str, DataContract]:
        """
        Serialize DataContracts from DataFrame

        :param df: DataFrame containing data contract data
        :param object_types: Dictionary of existing object types
        :param persons: Dictionary of existing persons
        :param session: SQLAlchemy session
        :return: Dictionary of created/updated data contracts
        """
        data_contracts = {}
        for _, row in df.iterrows():
            # Convert row to dictionary, replacing NaN with None
            contract_data = row.replace({np.nan: None}).to_dict()

            # Get corresponding object type
            object_type_name = contract_data.get('objectTypeName')
            object_type = object_types.get(object_type_name)

            if not object_type:
                print(f"Warning: No object type found for {object_type_name}")
                continue

            # Prepare owner and steward
            if contract_data.get('ownerEmail'):
                contract_data['owner'] = persons.get(contract_data['ownerEmail'], {})

            if contract_data.get('stewardEmail'):
                contract_data['steward'] = persons.get(contract_data['stewardEmail'], {})

            # Prepare JSON-compatible format
            prepared_contract_data = {
                k: v for k, v in contract_data.items()
                if v is not None
            }

            # Create data contract
            data_contract = DataContract.from_json(prepared_contract_data, object_type, session)
            data_contracts[f"{object_type.subgraph_name}_{object_type.name}"] = data_contract

        return data_contracts

    @classmethod
    def _serialize_documentation_references(
            cls,
            df: pd.DataFrame,
            data_contracts: Dict[str, DataContract],
            session: Session
    ):
        """
        Serialize DocumentationReferences from DataFrame

        :param df: DataFrame containing documentation reference data
        :param data_contracts: Dictionary of existing data contracts
        :param session: SQLAlchemy session
        """
        for _, row in df.iterrows():
            # Convert row to dictionary, replacing NaN with None
            ref_data = row.replace({np.nan: None}).to_dict()

            # Get corresponding data contract
            contract_key = f"{ref_data.get('subgraphName')}_{ref_data.get('objectTypeName')}"
            data_contract = data_contracts.get(contract_key)

            if not data_contract:
                print(f"Warning: No data contract found for {contract_key}")
                continue

            # Create documentation reference
            DocumentationReference.from_dict(
                ref_data,
                data_contract.subgraph_name,
                data_contract.object_type_name,
                session
            )

    @classmethod
    def export_to_excel(cls, session: Session, output_path: str):
        """
        Export all data from the database to an Excel workbook

        :param session: SQLAlchemy session
        :param output_path: Path to save the Excel file
        """
        # Create an Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Export Persons
            persons = session.query(Person).all()
            persons_df = pd.DataFrame([p.to_json() for p in persons])
            persons_df.to_excel(writer, sheet_name='Persons', index=False)

            # Export ObjectTypes
            object_types = session.query(ObjectType).all()
            object_types_data = []
            for ot in object_types:
                ot_json = ot.to_json()['definition']
                ot_json['subgraphName'] = ot.subgraph_name
                object_types_data.append(ot_json)
            object_types_df = pd.DataFrame(object_types_data)
            object_types_df.to_excel(writer, sheet_name='ObjectTypes', index=False)

            # Export ObjectFields
            object_fields = session.query(ObjectField).all()
            object_fields_data = []
            for of in object_fields:
                of_json = of.to_json()
                of_json['objectTypeName'] = of.object_type_name
                of_json['scalarTypeName'] = of.scalar_type_name
                object_fields_data.append(of_json)
            object_fields_df = pd.DataFrame(object_fields_data)
            object_fields_df.to_excel(writer, sheet_name='ObjectFields', index=False)

            # Export DataContracts
            data_contracts = session.query(DataContract).all()
            data_contracts_data = []
            for dc in data_contracts:
                dc_json = dc.to_json()
                dc_json['ownerEmail'] = dc.owner_email if dc.owner else None
                dc_json['stewardEmail'] = dc.steward_email if dc.steward else None
                data_contracts_data.append(dc_json)
            data_contracts_df = pd.DataFrame(data_contracts_data)
            data_contracts_df.to_excel(writer, sheet_name='DataContracts', index=False)

            # Export DocumentationReferences
            doc_refs = session.query(DocumentationReference).all()
            doc_refs_data = [dr.to_dict() for dr in doc_refs]
            doc_refs_df = pd.DataFrame(doc_refs_data)
            doc_refs_df.to_excel(writer, sheet_name='DocumentationReferences', index=False)
