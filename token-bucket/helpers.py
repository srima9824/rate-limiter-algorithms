from fastapi import Request, HTTPException

def get_client_identifier(request: Request) -> str:
    if not isinstance(request.client.host, str):
        raise HTTPException(status_code=400, detail="Client Id must be string")
    if not request.client.host:
        raise HTTPException(status_code=400, detail="Client Id cannot be empty")
    client_identifier = request.client.host.strip()
    return client_identifier
