import requests, os
def test_upload_verify():
    url = "http://localhost:5000/upload"
    with open("tests/sample.pdf","wb") as f: f.write(b"sample")
    files = {'file': open('tests/sample.pdf','rb')}
    r = requests.post(url, files=files, data={"issuer":"Test"})
    assert r.status_code == 200
    j = r.json()
    assert "hash" in j
