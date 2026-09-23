from dataclasses import dataclass

@dataclass
class User:
    username: str
    password: str
    role: str
    name: str

@dataclass
class Resource:
    resource_id: str
    name: str
    category: str
    location: str
    status: str = "Available"

@dataclass
class Complaint:
    complaint_id: str
    resource_id: str
    title: str
    description: str
    category: str
    priority: str
    reported_by: str
    status: str = "Pending"
    assigned_to: str = ""
