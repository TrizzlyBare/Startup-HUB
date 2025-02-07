from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import WebRTCSession
from .serializers import WebRTCSessionSerializer


@api_view(["POST"])
def create_offer(request):
    """Store SDP Offer in the database"""
    room = request.data.get("room")
    offer = request.data.get("offer")

    session, created = WebRTCSession.objects.get_or_create(room=room)
    session.offer = offer
    session.save()

    return Response({"message": "Offer stored successfully"})


@api_view(["GET"])
def get_offer(request):
    """Retrieve SDP Offer"""
    room = request.GET.get("room")
    session = WebRTCSession.objects.filter(room=room).first()

    if session and session.offer:
        return Response({"offer": session.offer})
    return Response({"error": "No offer found"}, status=404)


@api_view(["POST"])
def create_answer(request):
    """Store SDP Answer in the database"""
    room = request.data.get("room")
    answer = request.data.get("answer")

    session = WebRTCSession.objects.filter(room=room).first()
    if session:
        session.answer = answer
        session.save()
        return Response({"message": "Answer stored successfully"})

    return Response({"error": "Session not found"}, status=404)


@api_view(["GET"])
def get_answer(request):
    """Retrieve SDP Answer"""
    room = request.GET.get("room")
    session = WebRTCSession.objects.filter(room=room).first()

    if session and session.answer:
        return Response({"answer": session.answer})
    return Response({"error": "No answer found"}, status=404)


@api_view(["POST"])
def store_ice_candidate(request):
    """Store ICE Candidate"""
    room = request.data.get("room")
    candidate = request.data.get("candidate")

    session = WebRTCSession.objects.filter(room=room).first()
    if session:
        session.ice_candidates.append(candidate)
        session.save()
        return Response({"message": "ICE Candidate stored"})

    return Response({"error": "Session not found"}, status=404)


@api_view(["GET"])
def get_ice_candidates(request):
    """Retrieve ICE Candidates"""
    room = request.GET.get("room")
    session = WebRTCSession.objects.filter(room=room).first()

    if session:
        return Response({"candidates": session.ice_candidates})

    return Response({"error": "No candidates found"}, status=404)
